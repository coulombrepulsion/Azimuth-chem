"""SpectrumWorkspace: module-owned pages and operations. Contract: docs/MODULES.md."""

from pathlib import Path
from PySide6.QtWidgets import QTableWidgetItem, QFileDialog, QPushButton
from PySide6.QtCore import Qt
from modules.spectrum.readers.outputs import read_any

from azimuth.paths import ROOT
from azimuth.i18n import tr


# a page of the panel of Compass -> the tab of the result in Spectrum with the same thing
SPECTRUM_TABS = {'steps': 'convergence_tab', 'modes': 'vibrations_tab', 'surfaces': 'field_tab', 'aim': 'topology_tab',
                 'orbitals': 'dos_tab'}  # the orbitals — their density of states


_AUX_SEEN = {}  # (path, size, mtime): whether a MOPAC .aux has orbitals


def aux_has_orbitals(path):
    """Mopac_orbitals.has_orbitals of a .aux without reading all of it into
    memory — its header, then the file in 1 MB pieces until EIGENVECTORS[ starts a line; remembered while the file is
    not changed (find_molden runs at every showing of a result)."""
    import re

    from azimuth.runtime.provenance import fingerprint

    key = fingerprint(path)  # by its content
    if key is None:
        raise OSError(f'{path}: cannot be read')
    if key in _AUX_SEEN:
        return _AUX_SEEN[key]
    found = False
    pattern = re.compile(r'(?:^|\n)\s*(?:ALPHA_)?EIGENVECTORS\[')
    with open(path, encoding='utf-8', errors='replace') as f:
        head = f.read(4000)
        if 'START OF MOPAC FILE' in head:
            tail = '\n' + head
            while True:
                if pattern.search(tail):
                    found = True
                    break
                piece = f.read(1_000_000)
                if not piece:
                    break
                tail = tail[-200:] + piece
    _AUX_SEEN[key] = found
    return found

from azimuth.window_port import part  # noqa: E402
from modules.spectrum import results_page as _page
from modules.spectrum.results_page import EMPTY_RESULT
from modules.spectrum import result_analyses as _analyses
from modules.spectrum import result_orbitals as _orbitals


class SpectrumWorkspace:
    # «Инструменты» of Spectrum (isotopes, energies of files, Boltzmann) — a part of its own with a PORT
    spectrum_tools = property(lambda self: part(self, 'spectrum_tools', 'modules.spectrum.views.tools_view',
                                                'SpectrumToolsTool'))

    results_page = _page.results_page

    def refresh_result_tools(self):
        """The tools of the result shown for the group of the page: those of the orbitals on «Волновая
        функция», the reaction diagram on «Результат»; the folder always."""
        tabs = getattr(self, 'result_tabs', None)
        if tabs is None or not hasattr(self, 'wave_tools'):
            return
        group = tabs.group_of(tabs.currentIndex())
        self.wave_tools.setVisible(group == tr('Волновая функция'))
        self.energy_tools.setVisible(group == tr('Результат') or tabs.currentIndex() == 0)
        self.refresh_tools_bar()

    def refresh_tools_bar(self):
        """The row over the page only when it has something — the list of the pages of the group or a tool
        of the result shown."""
        tabs = getattr(self, 'result_tabs', None)
        bar = getattr(tabs, 'bar', None) if tabs is not None else None
        if bar is None or not hasattr(self, 'wave_tools'):
            return
        tools = [w for box in (self.wave_tools, self.energy_tools) if not box.isHidden()
                 for w in box.findChildren(QPushButton) if not w.isHidden()]
        bar.setVisible(not tabs.chooser.isHidden() or bool(tools))

    def show_crystal_results(self, manifest, title=''):
        """Spectrum of a project of a crystal: the results of its runs (CrystalResultsView)."""
        from modules.spectrum.views.crystal_view import CrystalResultsView

        if self.crystal_results is None:
            self.crystal_results = CrystalResultsView(self)
            self.results_stack.addWidget(self.crystal_results)
        self.crystal_results.show_project(manifest, title)
        self.results_stack.setCurrentWidget(self.crystal_results)
        return self.crystal_results

    def display_output(self, text, source, show=True, path=None, output=None):
        """Read a result and show it. The result gets its tab (modules/compass/panels/documents.route_result) —
        the same one in Compass, Sextant and Spectrum — and then Spectrum shows it (show_result). Output —
        already read (in the background, open_output_path)."""
        if output is None:
            output = self.read_result(text, path)
        record = (output, text, source, path)
        if hasattr(self, 'route_result'):
            self.route_result(record)
        else:
            self.trajectory_tool.load_trajectory(output, source)
        self.show_result(record)
        if hasattr(self, 'result_orbitals_note') and not show:
            self.result_orbitals_note()
        if show:
            self.navigate(2)
        return output

    def show_result(self, record):
        """Spectrum shows the result record (output, text, source, path) of the current tab; Compass is not touched."""
        output, text, source, path = record
        self.output = output
        self.output_text, self.output_path = text, path  # for the reaction diagram
        self.show_empty_quill(False)
        if hasattr(self, 'trajectory_tool'):  # the page «Частоты» of the drawer of Compass
            self.trajectory_tool.load_result_modes(output)
        self.vibrations.set_playing(False)
        self.reaction_button.setEnabled(bool(output.energies or output.final_energy))
        self.reaction_button.setVisible(self.reaction_button.isEnabled())
        self.result_folder_button.setVisible(bool(getattr(self, 'output_path', None)))
        self.refresh_tools_bar()
        self.output_source.setText(
            (tr('УЧЕБНЫЙ ПРИМЕР — НЕ РЕАЛЬНЫЙ РАСЧЁТ · ') if output.demo else '') + source + ' · ' + output.program
        )
        self.result_summary.setText(self.summary_text(output))
        self.flash_status()
        return self._show_rest(output, text, source, path, record)

    STATUS_MS = 8000  # as the message of Compass (notify)

    def flash_status(self, ms=None):
        """The status of the result on its pill for a while (as Compass's notify)."""
        pill = getattr(self, 'status_pill', None)
        if pill is None:
            return
        if getattr(self, 'output', None) is None or not (self.output_source.text() or self.result_summary.text()):
            pill.hide()
            return
        pill.show()
        self.place_status()
        self.status_timer.start(self.STATUS_MS if ms is None else ms)

    def status_note(self, text, ms):
        """Text as the last line of the pill of the status, shown — for ms, the pill staying as long."""
        self.status_message.setText(text)
        self.status_message.show()
        self.place_status()
        self.status_message_timer.start(ms)
        if self.status_timer.remainingTime() < ms:
            self.status_timer.start(ms)

    def drop_status_note(self):
        self.status_message_timer.stop()
        self.status_message.clear()
        self.status_message.hide()
        if not self.status_pill.isHidden():
            self.place_status()

    def place_status(self):
        """The pill of the status at the foot of the panel of the result, at the left (as wide as its
        lines, the long assessment wrapped), the spectrum of a running calculation at the right."""
        panel = getattr(self, 'result_panel', None)
        pill = getattr(self, 'status_pill', None)
        if panel is None or pill is None:
            return
        pulse = getattr(self, 'calc_pulse', None)
        margin = 16
        room = 0
        if pulse is not None:
            pulse.adjustSize()
            size = pulse.sizeHint()
            pulse.resize(size)
            pulse.move(panel.width() - size.width() - margin, panel.height() - size.height() - margin)
            pulse.raise_()
            room = size.width() + 12 if pulse.isVisible() else 0
        lines = [w for w in (self.output_source, self.result_summary, self.assessment, self.status_message) if w.text()]
        natural = max([w.fontMetrics().horizontalAdvance(w.text()) for w in lines] or [120]) + 28 + 4
        width = max(160, min(natural, panel.width() - 2 * margin - room, 760))
        pill.setFixedWidth(width)
        layout = pill.layout()
        height = layout.totalHeightForWidth(width) if layout.hasHeightForWidth() else layout.totalSizeHint().height()
        # the lines measured themselves at the width they get — a wrapped one is as high as its wrapped text
        from PySide6.QtCore import QRect

        margins = layout.contentsMargins()
        inner = max(1, width - margins.left() - margins.right())
        shown = [layout.itemAt(i).widget() for i in range(layout.count())]
        shown = [w for w in shown if w is not None and not w.isHidden() and w.text()]
        measured = sum(w.fontMetrics().boundingRect(QRect(0, 0, inner, 100000), int(Qt.TextFlag.TextWordWrap)
                                                    if w.wordWrap() else 0, w.text()).height() + 2 for w in shown)
        measured += margins.top() + margins.bottom() + layout.spacing() * max(0, len(shown) - 1)
        pill.setFixedHeight(max(height, measured, layout.totalMinimumSize().height()))
        # in the middle of the panel, as
        # the message of Compass; left of the spectrum of a running calculation when they would meet
        x = (panel.width() - width) // 2
        x = max(margin, min(x, panel.width() - margin - room - width))
        pill.move(x, panel.height() - pill.height() - margin)
        pill.raise_()

    @staticmethod
    def steps_text(output):
        """« за 14 шагов» of an optimization (several steps), else ''."""
        n = len(getattr(output, 'steps', ()) or ())
        if n < 2:
            return ''
        if n % 10 == 1 and n % 100 != 11:
            return tr(' за {} шаг').format(n)
        if n % 10 in (2, 3, 4) and n % 100 not in (12, 13, 14):
            return tr(' за {} шага').format(n)
        return tr(' за {} шагов').format(n)

    def summary_text(self, output):
        """The termination, the optimization and the energy in one line of the status."""
        return (
            tr('Завершение: ')
            + output.termination_status
            + tr('   /   Оптимизация: ')
            + (tr('сошлась') if output.optimization_converged else tr('не подтверждена'))
            + self.steps_text(output)  # the steps here, not over the plots of «Сходимость»
            + tr('\nПоследняя энергия: ')
            + (tr(f'{output.energies[-1]:.10f} хартри') if output.energies
               else tr(f'теплота образования {output.heat_of_formation:.3f} ккал/моль (MOPAC, не полная энергия)')
               if getattr(output, 'heat_of_formation', None) is not None else tr('не найдена'))
            + (
                tr(f' (SCF); {output.final_energy[0]}: {output.final_energy[1]:.7f} хартри')
                if output.final_energy
                else ''
            )
            + (  # TD-DFT — the ground state above, the followed excited state here
                tr(f' (основное состояние); возбуждённое (корень {output.excited_energy[0]}): '
                   f'{output.excited_energy[1]:.10f} хартри')
                if getattr(output, 'excited_energy', None)
                else ''
            )
            + self.scan_summary(output.scan)
        ).replace('\n', '   ·   ')  # one line

    def _show_rest(self, output, text, source, path, record):
        """The rest of show_result: the tables, the tab shown, the orbitals, the panels."""
        # «Колебания и ИК» only when there is something to show there
        self.result_tabs.setTabVisible(self.vibrations_tab, bool(output.frequencies or output.modes))
        self._fill_result(output, text, path)
        if any(m.animatable for m in output.modes):
            self.result_tabs.setCurrentIndex(1)
        elif output.absorption:
            self.result_tabs.setCurrentIndex(self.uv_tab)
        elif output.shieldings:
            self.result_tabs.setCurrentIndex(self.nmr_tab)
        else:
            self.result_tabs.setCurrentIndex(0)
        self.update_result_geometry()
        self.sibling_molden = self.find_molden(path)
        if self.sibling_molden is None and path is not None and self.has_printed_orbitals(text):
            self.sibling_molden = Path(path)  # the output itself: print[p_mos] and print[p_basis] 2
        gbw = Path(path).with_suffix('.gbw') if path else None  # ORCA keeps the orbitals in <name>.gbw
        self.sibling_gbw = gbw if self.sibling_molden is None and gbw is not None and gbw.is_file() else None
        self.orbitals_button.setVisible(self.result_orbitals() is not None)
        self.result_tabs.setTabVisible(self.field_tab, self.result_orbitals() is not None)
        self.result_tabs.setTabVisible(self.topology_tab, self.result_orbitals() is not None)
        self.dos_panel.clear()  # the orbitals of this result are read when the tab is opened
        self.result_tabs.setTabVisible(self.dos_tab, self.result_orbitals() is not None)
        self.result_tabs.setTabVisible(self.deloc_tab, self.result_orbitals() is not None)
        if self.result_orbitals() is not None:
            self.deloc_panel.show_result()
        self.dos_shown(self.result_tabs.currentIndex())
        geometry = self.result_geometry()
        self.field_panel.set_atoms(len(geometry.atoms) if geometry is not None else 1,
                                   [a.symbol for a in geometry.atoms] if geometry is not None else None)
        self.field_panel.forget_saved()  # a new result — its kept map and profile, when the tab is opened
        self.density_compass_button.setVisible(self.result_orbitals() is not None and hasattr(self, 'density_tool'))
        self.refresh_tools_bar()
        if hasattr(self, 'density_tool'):  # the panel of the density in Compass
            self.density_tool.update_density_button()
        self.refresh_topology_tab()
        self.topology_shown(self.result_tabs.currentIndex())  # that tab on screen — its kept points
        self.deloc_shown(self.result_tabs.currentIndex())
        self.field_shown(self.result_tabs.currentIndex())

    find_result_topology = _analyses.find_result_topology
    topology_found = _analyses.topology_found
    field_shown = _analyses.field_shown
    deloc_shown = _analyses.deloc_shown
    topology_shown = _analyses.topology_shown
    saved_topology_here = _analyses.saved_topology_here
    refresh_topology_tab = _analyses.refresh_topology_tab
    excitation_source = _analyses.excitation_source
    transfer_context = _analyses.transfer_context
    show_nto = _analyses.show_nto
    dos_orbitals = _analyses.dos_orbitals
    dos_shown = _analyses.dos_shown

    def result_orbitals(self):
        """Where the orbitals of the shown result are: a Molden/fchk file, the output itself or an ORCA .gbw."""
        return getattr(self, 'sibling_molden', None) or getattr(self, 'sibling_gbw', None)

    def _fill_result(self, output, text, path):
        for table, rows in [
            (self.energy_table, [(i + 1, f'{e:.10f}') for i, e in enumerate(output.energies)]),
            (self.frequency_table, [(i, f'{f:.2f}') for i, f in output.frequencies]),
        ]:
            table.setRowCount(len(rows))
            for i, row in enumerate(rows):
                for j, value in enumerate(row):
                    table.setItem(i, j, QTableWidgetItem(str(value)))
        self.assessment.setText(output.assessment)
        self.vibrations.load(output)
        self.vibrations.source_path = self.uv_panel.source_path = path  # the first of the conformers
        geometry = output.geometry or output.vibration_geometry
        self.vibrations.source_formula = self.uv_panel.source_formula = geometry.formula if geometry else ''
        try:  # the scaling factor of the frequencies for the method and basis of this result
            from modules.spectrum.analysis.reaction import level_of_theory

            level = level_of_theory(text, getattr(output, 'program', ''))
        except Exception:  # noqa: BLE001 — a suggestion only
            level = ''
        self.vibrations.set_level(level)
        self.uv_panel.load(output.absorption)
        from modules.spectrum.analysis import emission  # an optimization of an excited state

        try:
            self.uv_panel.set_emission(emission.read(text, getattr(output, 'program', '')) if output.absorption else None)
        except (ValueError, IndexError):  # a part of a job: no emission said rather than a wrong one
            self.uv_panel.set_emission(None)
        from modules.spectrum.analysis import nto

        self.uv_panel.set_ntos(nto.read_ntos(text) if output.absorption and path else {})
        # the NMR reference per level; the input of the result builds the TMS job
        self.nmr_panel.load(output.shieldings, output.geometry, level, text, getattr(output, 'program', ''),
                            getattr(output, 'couplings', ()))
        self.result_tabs.setTabVisible(self.uv_tab, bool(output.absorption))
        self.result_tabs.setTabVisible(self.nmr_tab, bool(output.shieldings))
        from modules.spectrum.analysis.convergence import history

        self.result_tabs.setTabVisible(self.thermo_tab, self.thermo_panel.load(output, text))
        self.result_tabs.setTabVisible(self.convergence_tab, self.convergence_panel.load(history(output, text, path)))

    def show_empty_quill(self, empty):
        """The picture stands next to «В этой вкладке результата ещё нет» only. Both in the middle of
        the first tab instead of its cards; the status at the foot is hidden while there is no result."""
        shown = bool(empty) and not self.empty_quill.pixmap().isNull()
        self.empty_quill.setVisible(shown)
        if hasattr(self, 'empty_page'):
            self.empty_page.setVisible(bool(empty))
            self.frequency_table.setVisible(not empty)
            for item in (self.output_source, self.result_summary):
                item.setVisible(not empty)
            if empty and hasattr(self, 'status_pill'):
                self.status_timer.stop()
                self.status_pill.hide()
        return shown

    def clear_result(self):
        """A tab without a result — Spectrum is empty (the result of another tab stays in that tab)."""
        from modules.spectrum.readers.results import Output

        empty = Output(False, False, False, (), (), None, False)
        self.output = None
        self.output_text, self.output_path = '', None
        self.vibrations.set_playing(False)
        self.output_source.setText('')  # the hint is next to Quill, in the status
        self.result_summary.setText(tr(EMPTY_RESULT))
        self.show_empty_quill(True)
        if hasattr(self, 'trajectory_tool'):
            self.trajectory_tool.load_result_modes(None)
        try:
            self._fill_result(empty, '', None)
        except Exception:  # noqa: BLE001 — an empty result must not stop switching the tabs
            pass
        self.assessment.setText(
            tr('Нормальное завершение, сходимость оптимизации и проверка частот — разные условия. Здесь они рассматриваются отдельно.')
        )
        self.result_tabs.setCurrentIndex(0)
        self.reaction_button.setEnabled(False)
        self.reaction_button.setVisible(False)
        self.result_folder_button.setVisible(False)
        self.sibling_molden = None
        self.sibling_gbw = None
        self.orbitals_button.setVisible(False)
        self.density_compass_button.setVisible(False)
        self.refresh_tools_bar()
        self.result_tabs.setTabVisible(self.field_tab, False)  # no orbitals — no maps and no points
        self.result_tabs.setTabVisible(self.vibrations_tab, False)
        self.result_tabs.setTabVisible(self.topology_tab, False)
        self.result_tabs.setTabVisible(self.dos_tab, False)
        self.result_tabs.setTabVisible(self.deloc_tab, False)
        self.dos_panel.clear()
        if hasattr(self, 'density_tool'):
            self.density_tool.update_density_button()
        self.refresh_topology_tab()
        self.update_result_geometry()

    def reaction_diagram(self):
        """The window «Диаграмма реакции» (one per session; shown again if hidden)."""
        from modules.spectrum.views.reaction_view import ReactionWindow

        window = getattr(self, 'reaction_window', None)
        if window is None:
            window = ReactionWindow(self)
            self.reaction_window = window
        window.show()
        window.raise_()
        window.activateWindow()
        return window

    def add_result_to_reaction(self):
        """The current result of Spectrum as a new stage of the reaction diagram."""
        output = getattr(self, 'output', None)
        if output is None:
            return None
        from modules.spectrum.analysis import reaction

        try:
            path = getattr(self, 'output_path', None)
            species = reaction.species_from_output(output, getattr(self, 'output_text', '') or '', path or '')
        except ValueError as exc:
            self.error(exc)
            return None
        window = self.reaction_diagram()
        window.add_species(species)
        return window

    def open_result_file(self):
        """«Файл → Открыть результат расчёта…» (not open_output: that name is «Вывод программы» of Sextant)."""
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr('Открыть результат расчёта'),
            str(Path.home()),
            tr('ORCA, Gaussian, xtb, Psi4, NWChem, Q-Chem, GAMESS, MOPAC (*.out *.log *.nwout *.qcout *.gamout);;Все файлы (*)'),
        )
        if path and not (hasattr(self, 'open_output_in_its_project') and self.open_output_in_its_project(path)):
            self.open_output_path(path)  # an output of a project opens its project (open_output_in_its_project)

    BACKGROUND_BYTES = 2_000_000  # bigger outputs are read and parsed in the background

    def read_result(self, text, path=None):
        """The result of an output text — pure (no widgets), so it may run in a worker thread."""
        output = read_any(text, path)  # ORCA, Gaussian, xtb, Psi4; NWChem, Q-Chem, GAMESS
        return self.attach_irc_trajectory(output, path)

    def open_output_path(self, path, show=True, done=None):
        """Read an output (also from the hub home page, 'continue'); remembered as the last result. A file
        bigger than BACKGROUND_BYTES is read and parsed in a worker thread (azimuth/tasks.py) — the window keeps
        answering; it is shown when ready, in the tab chosen when it was asked for (result_target); done() runs after
        it is shown (at once for a small file) — also after a failure, as (the steps drawer, the end
        of a calculation). Returns True when shown, None when it is being read or failed."""
        try:
            size = Path(path).stat().st_size
            from modules.spectrum.readers.results import MAX_BYTES, too_large

            if size > MAX_BYTES:  # 256 MB (was 32)
                raise too_large()
        except (ValueError, OSError) as exc:
            self.error(exc)
            if done is not None:
                done()
            return None
        source = Path(path).name
        if size <= self.BACKGROUND_BYTES:
            try:
                self.display_output(Path(path).read_text(encoding='utf-8', errors='replace'), source, show, path)
                self.remember_recent('output', path)
            except (ValueError, OSError) as exc:
                self.error(exc)
                if done is not None:
                    done()
                return None
            if done is not None:
                done()
            return True
        from azimuth.tasks import Tasks

        if getattr(self, 'tasks', None) is None:
            self.tasks = Tasks(self)
        target = getattr(self, 'result_target', None)

        def work():
            text = Path(path).read_text(encoding='utf-8', errors='replace')
            return text, self.read_result(text, path)

        def shown(result):
            text, output = result
            self.result_target = target
            try:
                self.display_output(text, source, show, path, output)
                self.remember_recent('output', path)
            except ValueError as exc:
                self.error(exc)
            else:
                if hasattr(self, 'notify'):
                    self.notify(tr(f'Открыт результат: {source}.'), 4000)
            finally:
                self.result_target = None
            if done is not None:
                done()

        def failed(exc):
            self.error(exc if isinstance(exc, (ValueError, OSError)) else ValueError(str(exc)))
            if done is not None:
                done()

        if hasattr(self, 'notify'):
            self.notify(tr(f'Читаю {source} ({size / 1e6:.0f} МБ)… окно можно не ждать.'), 60000)
        self.tasks.run(('output', str(Path(path).resolve())), work, shown, failed)
        return None

    def attach_irc_trajectory(self, output, path):
        """The geometries of an IRC path: ORCA writes them to <name>_IRC_Full_trj.xyz next to the output."""
        scan = output.scan
        if scan is None or scan.kind != 'irc' or path is None:
            return output
        from dataclasses import replace
        from modules.spectrum.readers.orca_scan import with_trajectory

        trajectory = Path(path).with_name(Path(path).stem + '_IRC_Full_trj.xyz')
        try:
            return replace(output, scan=with_trajectory(scan, trajectory.read_text(encoding='utf-8', errors='replace')))
        except (OSError, ValueError, IndexError):
            return output

    @staticmethod
    def scan_summary(scan):
        if scan is None:
            return ''
        if scan.kind == 'irc':
            return tr(f'\nПуть IRC: {len(scan.points)} шагов — в Компасе (☰ над моделью).')
        return tr(f'\nСкан ППЭ: {len(scan.points)} точек — в Компасе (☰ над моделью).')

    def demo_output(self):
        try:
            self.display_output(
                (ROOT / 'examples' / 'teaching-demo.out').read_text(encoding='utf-8'), 'teaching-demo.out'
            )
        except (ValueError, OSError) as exc:
            self.error(exc)

    def demo_vibrations(self):
        try:
            self.display_output(
                (ROOT / 'examples' / 'vibrations-demo.out').read_text(encoding='utf-8'), 'vibrations-demo.out'
            )
        except (ValueError, OSError) as exc:
            self.error(exc)

    def result_geometry(self):
        if not self.output:
            return None
        if self.result_tabs.currentIndex() == 1:
            return self.output.vibration_geometry
        return self.output.geometry

    def update_result_geometry(self, *args):
        self.use_geometry.setEnabled(self.result_geometry() is not None)
        self.use_geometry.setText(
            tr('Взять исходную геометрию') if self.result_tabs.currentIndex() == 1 else tr('Взять последнюю геометрию')
        )

    def adopt_geometry(self):
        geometry = self.result_geometry()
        if geometry and self.confirm_replace():
            self.load_molecule(geometry)
            self.navigate(0)
            self.statusBar().showMessage(
                tr('Геометрия перенесена. Проверьте заряд и мультиплетность: они не извлекались из результата.'), 15000
            )

    def open_tms_input(self, kind, text, level):
        """The TMS input at the level of the shown result goes to Sextant as the edited input (run as is);
        the file is kept in «nmr-reference» of the jobs folder."""
        import re

        if not hasattr(self, 'input_tool'):
            return None
        root = self.run_tool.jobs_root() if hasattr(self, 'run_tool') else Path.home()
        slug = re.sub(r'[^A-Za-z0-9._-]+', '_', level).strip('_') or 'level'
        path = Path(root) / 'nmr-reference' / f'TMS_{slug}{".gjf" if kind == "gaussian" else ".inp"}'
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding='utf-8')
        except OSError as exc:
            self.error(exc)
            return None
        if self.input_tool.open_input_file(str(path)) is None:
            return None
        self.statusBar().showMessage(
            tr('TMS этим уровнем — в Секстанте. Запустите расчёт и откройте результат в Спектре: опора запомнится '
               'для уровня ') + level, 15000)
        return path

    def vibration_in_compass(self, row):
        """The vibration chosen in «Колебания и ИК» on the model of Compass (the page «Частоты» of the panel)."""
        if not hasattr(self, 'trajectory_tool'):
            return False
        self.trajectory_tool.set_trajectory_open(True, 'modes')
        table = self.drawer.modes_table
        if 0 <= row < table.rowCount():
            table.selectRow(row)
        return True

    def result_folder(self):
        """«Анализ» next to the file of the orbitals of the result (or next to the output) when it is there — the tables
        of the critical points, the maps, DOS, CDA… —, else the folder of the output; None without a result."""
        path = getattr(self, 'output_path', None)
        if not path:
            return None
        from modules.spectrum.wavefunction.field_tables import ANALYSIS

        places = [Path(p).parent for p in (self.result_orbitals(), path) if p]
        for folder in places:
            if (folder / ANALYSIS).is_dir():
                return folder / ANALYSIS
        return places[-1]

    def open_result_folder(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        folder = self.result_folder()
        if folder is None:
            return None
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        return folder

    def open_spectrum_for(self, page=''):
        """«Перейти в Спектр» of the panel of Compass: Spectrum with the tab of the result that has the same
        thing as the page of the panel — the steps (Сходимость), the vibrations, the maps, the critical points; the tab
        shown stays for the other pages (orbitals, conformers, structures)."""
        self.navigate(2)
        name = SPECTRUM_TABS.get(page)
        index = getattr(self, name, None) if name else None
        if index is not None and self.result_tabs.isTabVisible(index):
            self.result_tabs.setCurrentIndex(index)
        return self.result_tabs.currentIndex()

    def adopt_displaced(self, molecule, text):
        """A geometry displaced along a normal mode (Spectrum → Колебания) becomes the Compass model."""
        if molecule is not None and self.confirm_replace():
            from dataclasses import replace

            self.load_molecule(replace(molecule, title=''))
            self.navigate(0)
            self.statusBar().showMessage(
                tr('Смещённая геометрия перенесена в Компас: ') + text + tr('. Проверьте заряд и мультиплетность.'), 15000
            )

    cube_window = _orbitals.cube_window
    cube_closed = _orbitals.cube_closed
    open_cube = _orbitals.open_cube

    BACKGROUND_BYTES = 4_000_000

    def read_heavy(self, path, title, read):
        """Read() — reading and parsing a file — of a file over 4 MB in a worker
        thread while the window paints and shows its progress window (run_waiting: modal, so nothing changes under the
        work; the widgets are made after, here); a smaller file is read at once."""
        if Path(path).stat().st_size < self.BACKGROUND_BYTES:
            return read()
        from azimuth.tasks import run_waiting

        return run_waiting(self, title, lambda step: read(), alone=False)

    @staticmethod
    def find_molden(path):
        """<stem>.molden.input (orca_2mkl), .molden, .molf, a Gaussian .fchk or a MOPAC .aux with orbitals next
        to an output, else None."""
        if path is None:
            return None
        base = Path(path)
        for name in (base.stem + '.molden.input', base.stem + '.molden', base.stem + '.molf', base.stem + '.fchk'):
            candidate = base.with_name(name)
            if candidate.is_file():
                return candidate
        aux = base.with_name(base.stem + '.aux')  # the orbitals of MOPAC
        if aux.is_file() and aux != base:
            try:
                if aux_has_orbitals(aux):  # read in pieces, remembered by size and time
                    return aux
            except OSError:
                pass
        return None

    @staticmethod
    def has_printed_orbitals(text):
        from modules.spectrum.readers.output_orbitals import has_orbitals  # GAMESS, NWChem, Q-Chem

        return ('MOLECULAR ORBITALS' in text and 'BASIS SET IN INPUT FORMAT' in text) or has_orbitals(text)

    open_sibling_orbitals = _orbitals.open_sibling_orbitals
    load_result_orbitals = _orbitals.load_result_orbitals
    result_molden_path = _orbitals.result_molden_path
    open_orbitals = _orbitals.open_orbitals
    open_orbitals_path = _orbitals.open_orbitals_path
    open_orbitals_text = _orbitals.open_orbitals_text
    show_orbital_cube = _orbitals.show_orbital_cube
    demo_cube = _orbitals.demo_cube


