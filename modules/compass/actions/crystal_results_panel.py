"""«Расчёт → Результаты расчётов» of «Компас · Кристалл» (2026-11-21
group 15 of the list: what the calculations of a crystal gave was scattered over the items of «Расчёт» and the tabs of
Spectrum, greyed or not, and nowhere was there a list of the runs with their energies).

§1 PURPOSE
    One panel beside the model (CrystalTool.dock) with the runs of the crystal shown (crystal_results.runs of its
    project): the program and the task, the time, the energy, the pressure, whether it converged; the result the file
    was read from (an output of CRYSTAL: crystal_projects.set_result) as the first row. The run chosen — its details
    (the energy per cell in Eh and eV, the band gap, the Fermi level, the steps, the cell of the last step) and its
    folder; the analyses of the last runs (the steps, the charges, AIM, Spectrum) as buttons, grey with a tooltip when
    there is nothing for them.
§4 SPECIFICATION
    rows(manifest) -> [dict(title, time, energy, pressure, state, run, details)]; show(studio) -> ResultsPanel | None.
§7 TESTS
    tests/gui/test_gui_files.py::test_the_results_of_a_crystal_beside_its_model.
"""

from PySide6.QtWidgets import (QAbstractItemView, QDialog, QHBoxLayout, QHeaderView, QLabel, QPlainTextEdit,
                               QTableWidget, QTableWidgetItem, QVBoxLayout)

from azimuth.i18n import tr
from azimuth.ui import action_button

HARTREE_EV = 27.211386245988


def _summary(result):
    """(energy Eh, pressure kbar, state, detail lines) of a result of cp2k.read / qe.read (None: not read)."""
    if result is None:
        return None, None, tr('нет выхода'), [tr('Файла выхода нет: расчёт не запускался или ещё идёт.')]
    energy = result.energy_hartree
    if energy is None and result.energy is not None:
        energy = result.energy / 2  # Ry
    pressure = result.pressures[-1] if result.pressures else None
    if result.error:
        state = tr('ошибка')
    elif result.converged or result.done:
        state = tr('сошёлся') if result.converged else tr('закончен')
    else:
        state = tr('не закончен')
    lines = []
    if energy is not None:
        lines.append(tr('Энергия ячейки: {} Eh ({} эВ)').format(f'{energy:.8f}', f'{energy * HARTREE_EV:.5f}'))
    if result.highest is not None and result.lowest is not None:
        lines.append(tr('Запрещённая зона: {} эВ (верх валентной {} эВ, низ проводимости {} эВ)').format(
            f'{result.lowest - result.highest:.3f}', f'{result.highest:.3f}', f'{result.lowest:.3f}'))
    elif result.fermi is not None:
        lines.append(tr('Уровень Ферми: {} эВ').format(f'{result.fermi:.3f}'))
    if pressure is not None:
        lines.append(tr('Давление: {} кбар').format(f'{pressure:.2f}'))
    if result.steps:
        lines.append(tr('Шагов: {}').format(result.steps))
    if result.error:
        lines.append(tr('Ошибка: ') + str(result.error))
    return energy, pressure, state, lines


def rows(manifest):
    """The rows of the panel: the result of the file first (if any), then the runs, the last first."""
    from azimuth import crystal_projects
    from modules.compass.chemistry import crystal_results

    out = []
    kept = (crystal_projects.info(manifest).get('result') or {}) if manifest else {}
    if kept.get('energy') is not None:
        pressure = crystal_projects.pressure(crystal_projects.info(manifest))
        out.append({'title': tr('Файл кристалла') + (' · ' + kept['method'] if kept.get('method') else ''),
                    'time': '', 'energy': float(kept['energy']),
                    'pressure': pressure * 10 if pressure is not None else None, 'state': tr('из файла'), 'run': None,
                    'details': [tr('Энергия и метод — из выхода, из которого прочитан кристалл.')]})
    for run in reversed(crystal_results.runs(manifest) if manifest else []):
        try:
            result = crystal_results.result(run)
        except (OSError, ValueError, IndexError):
            result = None
        energy, pressure, state, lines = _summary(result)
        try:
            table = crystal_results.steps_table(crystal_results.steps(run))
        except (OSError, ValueError, IndexError, TypeError):
            table = []
        if table:
            last = table[-1]
            lines.append(tr('Ячейка последнего шага: a = {}, b = {}, c = {} Å, V = {} Å³').format(
                f"{last['a']:.4f}", f"{last['b']:.4f}", f"{last['c']:.4f}", f"{last['volume']:.2f}"))
        lines.append(tr('Папка: ') + str(run.folder))
        out.append({'title': run.title, 'time': run.time, 'energy': energy, 'pressure': pressure, 'state': state,
                    'run': run, 'details': lines})
    return out


class ResultsPanel(QDialog):
    def __init__(self, studio, manifest):
        super().__init__(studio)
        self.studio, self.manifest = studio, manifest
        self.setWindowTitle(tr('Результаты расчётов'))
        layout = QVBoxLayout(self)
        head = QLabel('<b>' + tr('Результаты расчётов') + '</b>')
        layout.addWidget(head)
        self.rows = rows(manifest)
        self.note = QLabel('')
        self.note.setWordWrap(True)
        self.note.setObjectName('subtitle')
        layout.addWidget(self.note)
        self.table = QTableWidget(len(self.rows), 5)
        self.table.setHorizontalHeaderLabels([tr('Расчёт'), tr('Время'), tr('E, Eh'), tr('P, кбар'), tr('Итог')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        for i, row in enumerate(self.rows):
            texts = [row['title'], row['time'][:16].replace('T', ' '),
                     f"{row['energy']:.6f}" if row['energy'] is not None else '—',
                     f"{row['pressure']:.2f}" if row['pressure'] is not None else '—', row['state']]
            for j, text in enumerate(texts):
                self.table.setItem(i, j, QTableWidgetItem(text))
        self.table.itemSelectionChanged.connect(self.chosen_changed)
        layout.addWidget(self.table, 2)
        self.details = QPlainTextEdit()
        self.details.setReadOnly(True)
        layout.addWidget(self.details, 1)
        tools = QHBoxLayout()
        self.folder_button = action_button(tr('Папка расчёта'), self.open_folder, 'folder')
        tools.addWidget(self.folder_button)
        self.steps_button = action_button(tr('Шаги оптимизации'), self.show_steps, 'opt-steps')
        tools.addWidget(self.steps_button)
        tools.addStretch(1)
        layout.addLayout(tools)
        tools = QHBoxLayout()
        properties = getattr(studio, 'property_tool', None)
        self.charges_button = action_button(tr('Заряды…'), lambda: properties.compute_crystal_charges(), 'charges')
        tools.addWidget(self.charges_button)
        self.aim_button = action_button(tr('Связи AIM…'), lambda: properties.crystal_aim(), 'aim-bonds')
        tools.addWidget(self.aim_button)
        self.spectrum_button = action_button(tr('В Спектр'), lambda: studio.navigate(2), 'spectrum-crystal')
        tools.addWidget(self.spectrum_button)
        tools.addStretch(1)
        layout.addLayout(tools)
        buttons = QHBoxLayout()
        self.calc_button = action_button(tr('Посчитать в Секстанте…'), self.to_calculation, 'crystal-sextant')
        buttons.addWidget(self.calc_button)
        buttons.addStretch(1)
        buttons.addWidget(action_button(tr('Закрыть'), self.reject, 'close'))
        layout.addLayout(buttons)
        self.grey()
        if self.rows:
            self.table.selectRow(0)
        else:
            self.chosen_changed()

    def grey(self):
        """What has nothing to work on is grey, its tooltip says why (as the items of «Расчёт»)."""
        cp2k = None
        try:
            cp2k = self.studio.property_tool.crystal_run() if hasattr(self.studio, 'property_tool') else None
        except (OSError, ValueError, AttributeError):
            cp2k = None
        runs = [r for r in self.rows if r['run'] is not None]
        none = tr('Нет расчёта CP2K этого кристалла — посчитайте его в Секстанте.')
        for button, why in ((self.charges_button, None if cp2k else none), (self.aim_button, None if cp2k else none),
                            (self.steps_button, None if runs else tr('У этого кристалла ещё нет расчётов в проекте.')),
                            (self.spectrum_button, None if runs else tr('У этого кристалла ещё нет расчётов в проекте.'))):
            button.setEnabled(why is None)
            button.setToolTip(why or button.toolTip())
        if not self.manifest:
            self.note.setText(tr('Кристалл не в проекте: расчёты появятся здесь после «Посчитать в Секстанте…».'))
        elif not self.rows:
            self.note.setText(tr('У этого кристалла ещё нет расчётов в проекте.'))
        else:
            self.note.setText(tr('Последний расчёт — первым; строка показывает подробности.'))

    def chosen(self):
        rows = sorted({i.row() for i in self.table.selectedIndexes()})
        return self.rows[rows[0]] if rows else None

    def chosen_changed(self):
        row = self.chosen()
        self.details.setPlainText('\n'.join(row['details']) if row else '')
        self.folder_button.setEnabled(bool(row and row['run'] is not None))

    def open_folder(self):
        row = self.chosen()
        if not row or row['run'] is None:
            return None
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(row['run'].folder)))
        return row['run'].folder

    def show_steps(self):
        if not self.manifest or not self.studio.show_project_crystal_steps(self.manifest):
            self.studio.notify(tr('У этого кристалла нет оптимизации с шагами — посчитайте её в Секстанте.'), 7000)
            return False
        return True

    def to_calculation(self):
        self.studio.crystal_tool.to_calculation()


def show(studio):
    if not getattr(studio, 'crystal', None):
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    manifest = studio.research_path() if hasattr(studio, 'research_path') else None
    panel = ResultsPanel(studio, manifest)
    studio._results_panel = panel
    tool = getattr(studio, 'crystal_tool', None)
    if tool is not None and hasattr(tool, 'dock'):
        tool.dock(panel)
    else:
        panel.show()
    return panel
