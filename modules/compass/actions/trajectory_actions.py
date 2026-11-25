"""Compass: optimization steps drawer, browsing and adopting a step (moved from workspace.py)."""

from pathlib import Path
from dataclasses import replace
from math import dist
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QTableWidget,
    QTableWidgetItem,
    QFileDialog,
)
from modules.compass.chemistry.geometry_tools import BOHR

from azimuth.i18n import tr


class TrajectoryTool:
    """Was the mixin TrajectoryActions of the window; a part of its own — it reaches the window only through the names
    of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        '_coordinate_bohr',
        '_loading',
        '_own',
        'browsing',
        'build_mode',
        'compass_mode',
        'coordinate_tool',
        'crystal',
        'document',  # the file of the result of the tab («Открыть папку расчёта»)
        'crystal_tool',
        'density_tool',
        'dirty',
        'drawer',
        'edit_toggle',
        'error',  # a folder that cannot be opened
        'isVisible',
        'load_molecule',
        'lock_button',
        'molecule',
        'move_button',
        'navigate',
        'notify',
        'open_output_path',
        'place_notice',
        'stack',
        'symmetry_button',
        'table',
        'trajectory_button',
        'trajectory_initial',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    # -- optimization steps ------------------------------------------------------------
    def toggle_trajectory(self):
        opened = self.w.trajectory_button.isChecked()
        page = None
        d = self.w.drawer
        if opened and ((d.page() == 'steps' and not d.steps) or (d.page() == 'modes' and not d.modes)):
            available = self.w.density_tool.density_available() if self.w.has('density_tool') else False
            page = d.best_page(available)  # open on a page with something in it
        self.set_trajectory_open(opened, page, keep=True)

    def set_trajectory_open(self, opened, page=None, keep=False):
        """Open or close the drawer of the result; page — 'steps', 'modes', 'orbitals', 'aim' or 'conformers' (
        keep — the user closes the drawer (☰ or ✕): the step or the conformer chosen stays as the structure;
        every other closing — a tab switch, editing, a new result — goes back to the structure of the tab)."""
        self.w.trajectory_button.setChecked(opened)
        if opened:
            if self.w.stack.currentIndex() != 0:
                self.w.navigate(0)
            self.w.drawer.place(self.w.viewer.geometry())
            self.w.drawer.open_drawer(self.w.isVisible())
            self.w.viewer.set_inset(self.w.drawer.width(), self.w.isVisible())  # the model moves out from under it
            self.w.place_notice(animate=self.w.isVisible())  # the pill moves out from under it too
            if page is not None:
                self.w.drawer.set_page(page)
            else:
                self.apply_drawer_page(self.w.drawer.page())
            # entering the steps changes the rows above the field; place the drawer again once the layout
            # has settled (the first opening after a calculation left it lower than the field)
            from PySide6.QtCore import QTimer

            def again():
                try:
                    if self.w.drawer.isVisible():
                        self.w.drawer.place(self.w.viewer.geometry())
                        self.w.viewer.set_inset(self.w.drawer.width())
                except RuntimeError:  # the window is gone
                    pass

            for delay in (0, 300):
                QTimer.singleShot(delay, self.w.drawer, again)  # cancelled with the drawer
        else:
            self.w.drawer.set_mode_playing(False)
            self.w.drawer.close_drawer()
            self.w.viewer.set_inset(0, self.w.isVisible())
            self.w.place_notice(animate=self.w.isVisible())
            # the step chosen in «Оптимизация» stays in Compass when the drawer is closed (one undoable change)
            page_now = self.w.drawer.page()
            kept = None
            if keep and self.w.browsing and page_now == 'steps':
                kept = self.w.drawer.geometry_of_step
            elif keep and self.w.browsing and page_now == 'conformers':
                kept = self.w.drawer.geometry_of_conformer
            camera = self.w.viewer.locked_camera
            same = kept is not None and self.w._own is not None and \
                [a.symbol for a in kept.atoms] == [a.symbol for a in self.w._own[0].atoms]
            self.leave_trajectory(shown=kept if same else None)
            if same and kept.atoms != self.w.molecule.atoms:
                self.w.load_molecule(replace(kept, title=self.w.molecule.title), preserve_view=True)
                self.w.dirty = True
            if same and camera is not None:
                # the step stays where it was on the screen (before, the view was fitted again to it: a jump)
                self.w.viewer.locked_camera = camera
                self.w.viewer.update()

    def apply_drawer_page(self, name):
        """The model follows the page — a step of the optimization, the vibration chosen, or the structure of
        the tab under the orbitals and QTAIM."""
        if not self.w.trajectory_button.isChecked():
            return
        if name == 'steps' and self.w.drawer.steps:
            self.enter_trajectory()
            self.show_trajectory_step(self.w.drawer.current)
        elif name == 'conformers' and self.w.drawer.conformers:
            self.enter_trajectory()
            self.show_conformer(self.w.drawer.conformer_current)
        elif name == 'modes' and self.w.drawer.modes_base is not None:
            self.enter_trajectory()
            self.w.viewer.ghost = None
            self.show_molecule(replace(self.w.drawer.modes_base, title=''))
            self.w.viewer.locked_camera = None
            self.w.viewer.keep_camera()
            self.w.drawer.select_mode(self.w.drawer.mode_current)
        else:
            self.leave_trajectory()
            if name in ('orbitals', 'surfaces', 'aim') and self.w.has('density_tool'):
                self.w.density_tool.ensure_density_content()

    def calculation_file(self):
        """The file of the result of the tab (its output: ORCA, Gaussian, xtb, … — record path), or None."""
        from pathlib import Path

        document = self.w.document()
        record = getattr(document, 'output', None) if document is not None else None
        path = record[3] if isinstance(record, tuple) and len(record) > 3 else None
        return Path(path) if path and Path(path).is_file() else None

    def calculation_folder(self):
        """The folder of the calculation shown in the panel of steps: that of the optimization of a crystal
        (load_crystal_steps), else that of the result of the tab; None — the steps have no file (a path between
        structures, a scan about a bond)."""
        from pathlib import Path

        folder = getattr(self.w.drawer, 'folder', None)
        if folder and Path(folder).is_dir():
            return Path(folder)
        found = self.calculation_file()
        return found.parent if found is not None else None

    def open_calculation_folder(self):
        """«Открыть папку расчёта»: Finder (macOS) or Explorer (Windows) with the output selected, else the
        folder."""
        import subprocess
        import sys

        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        folder = self.calculation_folder()
        if folder is None:
            self.w.notify(tr('У этих шагов нет папки на диске: они построены в программе, а не прочитаны из расчёта.'), 6000)
            return None
        found = self.calculation_file() if getattr(self.w.drawer, 'folder', None) is None else None
        try:
            if found is not None and sys.platform == 'darwin':
                subprocess.Popen(['open', '-R', str(found)])
            elif found is not None and sys.platform.startswith('win'):
                subprocess.Popen(['explorer', '/select,', str(found)])
            else:
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        except OSError as exc:
            self.w.error(exc)
            return None
        return folder

    def update_result_button(self):
        """☰ is shown only when the tab has something for the drawer — steps (an optimization, a scan, a path),
        vibrations or orbitals; otherwise it is hidden (and an open drawer closes)."""
        d = self.w.drawer
        if hasattr(d, 'open_button'):  # «Открыть папку расчёта» — when the shown result has a folder
            d.open_button.setEnabled(self.calculation_folder() is not None)
        available = self.w.density_tool.density_available() if self.w.has('density_tool') else False
        shown = bool(d.steps or d.modes or d.conformers or available)
        if not shown and self.w.trajectory_button.isChecked():
            self.set_trajectory_open(False)
        self.w.trajectory_button.setVisible(shown)
        return shown

    def show_mode_frame(self, geometry):
        """A frame of the vibration on the model (only while the vibrations are shown in it)."""
        if geometry is None or not self.w.browsing or self.w.drawer.page() != 'modes':
            return
        self.w.viewer.set_molecule(geometry)
        self.w.viewer.moving()

    def load_result_modes(self, output):
        """The vibrations of the result of the tab for the page «Частоты» (None: no result)."""
        from modules.compass.chemistry.builder import connections

        modes = tuple(getattr(output, 'modes', ()) or ()) if output is not None else ()
        base = getattr(output, 'vibration_geometry', None) if output is not None else None
        if base is not None:
            base = replace(base, bonds=connections(base))
        if self.w.drawer.page() == 'modes' and self.w.browsing:
            self.leave_trajectory()
        self.w.drawer.load_modes(modes, base if modes else None)
        if self.w.trajectory_button.isChecked() and self.w.drawer.page() == 'modes':
            self.apply_drawer_page('modes')
        self.update_result_button()

    def load_trajectory(self, output, source=''):
        """Steps of the optimization in output (from Spectrum or the drawer); the start: the echoed input."""
        steps = tuple(output.steps) if output is not None else ()
        scan = getattr(output, 'scan', None)  # a surface scan or an IRC shows its points
        if scan is not None:
            from modules.spectrum.readers.results import OptimizationStep

            steps = tuple(OptimizationStep(p.number, p.energy, p.geometry) for p in scan.points)
        if self.w.browsing:
            self.leave_trajectory()
        first = next((s.geometry for s in steps if s.geometry is not None), None)
        initial = getattr(output, 'initial_geometry', None)
        if initial is None or first is None or [a.symbol for a in initial.atoms] != [a.symbol for a in first.atoms]:
            initial = first
        self.w.trajectory_initial = initial
        self.w.drawer.load(steps, source, scan)
        if self.w.drawer.isVisible() and steps:
            self.enter_trajectory()
            self.show_trajectory_step(self.w.drawer.current)
        self.update_result_button()

    def open_trajectory(self):
        path, _ = QFileDialog.getOpenFileName(
            self.w.widget,
            tr('Открыть результат расчёта'),
            str(Path.home()),
            tr('ORCA, Gaussian, xtb, Psi4, NWChem, Q-Chem, GAMESS, MOPAC (*.out *.log *.nwout *.qcout *.gamout);;Все файлы (*)'),
        )
        if path:
            self.w.open_output_path(path, show=False, done=lambda: self.set_trajectory_open(True, 'steps'))

    def enter_trajectory(self):
        if self.w.browsing:
            return
        self.w.browsing = True
        self.w._own = (self.w.molecule, self.w.dirty)
        self.w.build_mode.setCurrentIndex(0)
        for item in (self.w.edit_toggle, self.w.move_button, self.w.symmetry_button, self.w.lock_button):
            item.setEnabled(False)
        self._triggers = self.w.table.editTriggers()
        self.w.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.w.viewer.locked_camera = None

    def open_scan_map(self):
        """The map of the two-dimensional scan of the panel of steps; a click on a point selects it there."""
        from azimuth import defaults
        from modules.compass.panels.scan_map_view import ScanMapDialog

        if not self.w.drawer.is_map():
            self.w.notify(tr('Карта — для скана двух координат (двумерный скан ORCA).'), 6000)
            return None
        old = getattr(self, 'scan_map_dialog', None)
        if old is not None:
            old.close()
        dialog = ScanMapDialog(self.w.drawer.scan, defaults.energy_factor(), tr(defaults.energy_name()), self.w.widget)
        dialog.chosen.connect(self.w.drawer.select)
        dialog.show_point(self.w.drawer.current)
        self.scan_map_dialog = dialog
        dialog.show()
        return dialog

    def leave_trajectory(self, shown=None):
        """Back to the structure of the tab. Shown — the step that becomes the structure next (the drawer
        closed on it): the structure of the tab is not drawn for a moment in between (it flashed before the step)."""
        if not self.w.browsing:
            return
        self.w.browsing = False
        self.w.viewer.scan_pin = None
        molecule, dirty = self.w._own
        self.w._own = None
        self.w.viewer.ghost = None
        if shown is None:
            self.show_molecule(molecule)
        else:
            self.w.molecule = molecule  # the history gets the structure of the tab; the step is drawn by load_molecule
        self.w.dirty = dirty
        self.w.viewer.locked_camera = None
        crystal = getattr(self.w, 'crystal', None)  # the cell of the tab again after the cells of the steps
        if crystal and getattr(self.w, 'compass_mode', 'molecule') == 'crystal' and self.w.viewer.cell_lines is not None:
            from modules.compass.chemistry import crystal as cr

            self.w.viewer.cell_lines = cr.cell_edges(crystal[0].cell, crystal[1])
        for item in (self.w.edit_toggle, self.w.move_button, self.w.symmetry_button, self.w.lock_button):
            item.setEnabled(True)
        self.w.table.setEditTriggers(self._triggers)
        self.w.viewer.update()

    def show_molecule(self, molecule):
        """Show a structure in the field and the tables without history or the 'unsaved' mark."""
        dirty = self.w.dirty
        self.w._loading = True
        self.w.molecule = molecule
        self.w.table.blockSignals(True)
        self.w.table.setRowCount(len(molecule.atoms))
        for i, atom in enumerate(molecule.atoms):
            for j, value in enumerate((atom.symbol, *atom.position)):
                self.w.table.setItem(
                    i,
                    j,
                    QTableWidgetItem(str(value) if j == 0 else f'{value / (BOHR if self.w._coordinate_bohr else 1):.8f}'),
                )
        self.w.table.blockSignals(False)
        self.w.coordinate_tool.table_changed()
        self.w._loading = False
        self.w.dirty = dirty
        self.w.viewer.set_selection([])

    def show_trajectory_step(self, row):
        shown_map = getattr(self, 'scan_map_dialog', None)  # the map follows the step
        if shown_map is not None and shown_map.isVisible():
            shown_map.show_point(row)
        if not self.w.browsing or not 0 <= row < len(self.w.drawer.steps):
            return
        geometry = self.w.drawer.steps[row].geometry
        if getattr(self.w.drawer.steps[row], 'crystal', None) is not None:
            return self.show_crystal_step(row)  # a step of the optimization of a crystal
        if geometry is None:
            self.w.viewer.ghost = None
            self.w.viewer.update()
            self.w.drawer.set_shift('')
            return
        first = self.w.viewer.molecule is None or not self.w.viewer.molecule.atoms or self.w.viewer.locked_camera is None
        scan = getattr(self.w.drawer, 'scan', None)  # the scanned coordinate, measured on the model (orange)
        scanned = [c.atoms for c in getattr(scan, 'coordinates', ()) if getattr(c, 'atoms', ())] if scan else []
        self.w.viewer.scan_pin = tuple(scanned[0]) if scanned and scan.kind != 'irc' else None
        geometry = self.oriented_step(geometry)
        self.show_molecule(replace(geometry, title=''))
        if first:
            self.w.viewer.locked_camera = None
            self.w.viewer.keep_camera()
        ghost = None
        text = ''
        initial = self.w.trajectory_initial
        if (
            initial is not None
            and [a.symbol for a in initial.atoms] == [a.symbol for a in geometry.atoms]
            and initial.atoms != geometry.atoms
        ):
            try:
                from modules.spectrum.analysis.comparison import align

                ghost, rmsd = align(initial, geometry)
                shifts = [dist(a.position, b.position) for a, b in zip(ghost.atoms, geometry.atoms)]
                k = max(range(len(shifts)), key=shifts.__getitem__)
                text = tr(
                    f'От начальной: RMSD {rmsd:.3f} Å · наибольший сдвиг {shifts[k]:.3f} Å ({geometry.atoms[k].symbol}{k + 1})'
                )
            except ValueError:
                ghost = None
        self.w.viewer.ghost = ghost if self.w.drawer.initial.isChecked() else None
        self.w.drawer.set_shift(text)
        self.w.viewer.update()

    def show_crystal_step(self, row):
        """The crystal of the
        step with its cell, the start as faint atoms at the images nearest to the atoms of the step, the shift of the
        atoms and of the cell under the steps (modules/compass/chemistry/crystal_steps.py)."""
        from modules.compass.chemistry import crystal as cr
        from modules.compass.chemistry import crystal_steps as cs

        steps = self.w.drawer.steps
        step = steps[row]
        first = steps[0].crystal
        fit = self.w.viewer.molecule is None or not self.w.viewer.molecule.atoms or self.w.viewer.locked_camera is None
        self.show_molecule(step.geometry)
        self.w.viewer.cell_lines = cr.cell_edges(step.crystal.cell, (1, 1, 1))
        if fit:
            self.w.viewer.locked_camera = None
            self.w.viewer.keep_camera()
        try:
            change = cs.difference(first, step.crystal)
            text = cs.describe(change, step.crystal) if row else ''
            if step.adopted is not None and step.adopted is not step.crystal and not step.note:
                text += ('\n' if text else '') + tr('Взять: ячейка файла, группа {}').format(step.adopted.space_group)
            elif step.note:
                text += ('\n' if text else '') + tr('Взять: ') + step.note
            ghost = cs.ghost(first, step.crystal) if row and change.rmsd + abs(change.volume_percent) > 1e-6 else None
        except ValueError:
            text, ghost = '', None
        self.w.viewer.ghost = ghost if self.w.drawer.initial.isChecked() else None
        self.w.drawer.set_shift(text)
        self.w.viewer.update()

    def load_crystal_steps(self, steps, source='', folder=None):
        """The steps of an optimization of a crystal (crystal_steps.CrystalStep) into the drawer of the tab of
        that crystal, the last one chosen and shown; folder — that of its run («Открыть папку расчёта»)."""
        if self.w.browsing:
            self.leave_trajectory()
        self.w.trajectory_initial = steps[0].geometry if steps else None
        self.w.drawer.load(steps, source, None)
        self.w.drawer.folder = folder  # after load(), which forgets the folder of the steps before
        self.update_result_button()
        if steps:
            self.set_trajectory_open(True, 'steps')
            self.w.drawer.select(len(steps) - 1)

    def oriented_step(self, geometry):
        """0.91.72 («Настройки → Связи и шаги», как «Set common orientation for all geometries» Chemcraft): with
        common_orientation the step is turned and moved onto the starting geometry (Kabsch, a proper rotation) — a
        Gaussian optimization in the standard orientation or a scan no longer jumps on the screen. The table of
        coordinates and «Взять геометрию шага» get the turned step too (what is seen is what is taken; lengths and
        angles are the same)."""
        from azimuth import defaults

        initial = self.w.trajectory_initial
        if (not defaults.get('common_orientation') or initial is None or len(geometry.atoms) < 2
                or [a.symbol for a in initial.atoms] != [a.symbol for a in geometry.atoms]):
            return geometry
        from modules.spectrum.analysis.comparison import align

        try:
            return align(geometry, initial)[0]
        except ValueError:
            return geometry

    # -- conformers --------------------------------------------------------------------------
    def load_conformers(self, rows, source=''):
        """The conformers of a search on the page «Конформеры» of the drawer (they stay there until the next search)."""
        if self.w.browsing and self.w.drawer.page() == 'conformers':
            self.leave_trajectory()
        self.w.drawer.load_conformers(rows, source)
        self.update_result_button()

    def show_conformer(self, row):
        if not self.w.browsing or self.w.drawer.page() != 'conformers':
            return
        geometry = self.w.drawer.geometry_of_conformer
        if geometry is None:
            return
        first = self.w.viewer.locked_camera is None
        self.w.viewer.ghost = None
        own = self.w._own[0] if self.w._own else self.w.molecule
        self.show_molecule(replace(geometry, title='', bonds=own.bonds if len(own.atoms) == len(geometry.atoms) else geometry.bonds))
        if first:
            self.w.viewer.keep_camera()
        self.w.viewer.update()

    def adopt_conformer(self):
        geometry = self.w.drawer.geometry_of_conformer
        if geometry is None:
            return
        row = self.w.drawer.conformer_current
        self.set_trajectory_open(False)
        self.w.load_molecule(replace(geometry, title=self.w.molecule.title), preserve_view=True)
        self.w.dirty = True
        self.w.notify(tr(f'Взят конформер {row + 1}.'), 6000)

    def adopt_trajectory_step(self):
        current = self.w.drawer.current
        step = self.w.drawer.steps[current] if 0 <= current < len(self.w.drawer.steps) else None
        if getattr(step, 'crystal', None) is not None:  # the crystal of the step becomes the crystal of the tab
            chosen = step.adopted or step.crystal  # the cell of the file in its group when the step kept it
            self.set_trajectory_open(False)
            self.w.crystal_tool.build_crystal(chosen, (1, 1, 1), True)
            self.w.dirty = True
            said = tr('Ячейка и атомы шага {} перенесены в «Кристалл» · {}').format(step.cycle, chosen.space_group)
            self.w.notify(said + (' (' + step.note + ')' if step.note else ''), 12000)
            return
        geometry = self.w.drawer.geometry_of_step
        if geometry is None:
            return
        geometry = self.oriented_step(geometry)
        own, dirty = self.w._own if self.w._own else (self.w.molecule, self.w.dirty)
        self.set_trajectory_open(False)
        self.w.molecule = own
        self.w.load_molecule(replace(geometry, title=''))
        self.w.dirty = True
        self.w.notify(
            tr(
                'Геометрия шага перенесена в Компас. Проверьте заряд и мультиплетность: они не извлекались из результата.'
            ),
            12000,
        )

    def trajectory_key(self, event):
        """↑/← and ↓/→ step through the cycles, Home / End jump to the ends, space plays. On the page
        «Частоты» the same keys go through the vibrations."""
        if not self.w.browsing:
            return False
        key = event.key()
        d = self.w.drawer
        if d.page() == 'modes':
            moves = {Qt.Key.Key_Up: -1, Qt.Key.Key_Left: -1, Qt.Key.Key_Down: 1, Qt.Key.Key_Right: 1}
            if key in moves and d.modes:
                row = max(0, min(len(d.modes) - 1, d.mode_current + moves[key]))
                d.modes_table.setCurrentCell(row, 0)
                return True
            if key == Qt.Key.Key_Space:
                d.toggle_mode_playing()
                return True
            return False
        moves = {Qt.Key.Key_Up: -1, Qt.Key.Key_Left: -1, Qt.Key.Key_Down: 1, Qt.Key.Key_Right: 1}
        if d.page() == 'conformers':  # the same keys go through the list
            rows, current, select = d.conformers, d.conformer_current, d.select_conformer
            ends = {Qt.Key.Key_Home: 0, Qt.Key.Key_End: len(rows) - 1}
            if key in moves and rows:
                select(max(0, min(len(rows) - 1, current + moves[key])))
                return True
            if key in ends and rows:
                select(ends[key])
                return True
            return False
        if key in moves:
            d.select(d.current + moves[key])
            return True
        if key == Qt.Key.Key_Home:
            d.select(0)
            return True
        if key == Qt.Key.Key_End:
            d.select(len(d.steps) - 1)
            return True
        if key == Qt.Key.Key_Space:
            d.toggle_playing()
            return True
        return False
