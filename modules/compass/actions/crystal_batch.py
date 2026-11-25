"""The batch of crystals of a project: one calculation of Quantum ESPRESSO or CP2K for each crystal with a tick, one
after another, with the settings of the window.

§1 PURPOSE
    A batch of crystals. A crystal project holds several
    crystals (the series of calcium formate under pressure); in the batch mode of its list each crystal has a
    tick, and «Запустить расчёт» of the window of Quantum ESPRESSO / CP2K (QePanel, qe_window.py) computes all of them.
§2 ALGORITHM
    1. ask_and_run: a window says which crystals and asks the pressure of a relaxation with the cell (vc-relax of pw.x,
       CELL_OPT of CP2K): none, one for all (GPa), or each its own — that of the output of CRYSTAL it was read from
       (crystal_projects.pressure; a crystal without one — none). Other tasks: no question of pressure.
    2. CrystalBatch.next: the next crystal — its CIF of the project, put into the panel with the settings kept
       (QePanel.set_crystal_for_batch), its id and name for the folder and the record of the run (QePanel.batch_ident,
       batch_name), its pressure (QePanel.external); QePanel.start. A crystal that does not start (an element without
       its basis, no program) is noted and the next one goes.
    3. The 'end' of the panel (its listeners): the result noted (energy Eh, pressure of the output kbar, the cell volume),
       the list of the project read again, the next crystal after the event loop turns.
    4. At the end (or «Остановить» — the run under way stopped, the rest not started): the crystal shown before back in
       the panel, a table of the crystals (TableWindow).
§3 INTERFACE
    ask_and_run(panel, idents) -> CrystalBatch | None; run(panel, idents, pressure=None | float | 'own') ->
    CrystalBatch; CrystalBatch: rows (crystal, status, energy Eh, P kbar, V Å³), running, stop(), window (the table at
    the end).
§7 TESTS
    tests/gui/test_gui_files.py::test_a_batch_of_crystals (a fake pw.x).
"""

from PySide6.QtCore import QTimer

from azimuth.i18n import tr

CELL_TASK = 'Оптимизация с ячейкой'
OWN = 'own'


def _manifest(panel):
    from azimuth import crystal_projects

    root = panel.jobs_root()
    manifest = root.parent / 'project.qcc'
    if root.name != 'calculations' or not crystal_projects.is_crystal(manifest):
        raise ValueError(tr('Пакет кристаллов считается в проекте кристаллов.'))
    return manifest


def ask_and_run(panel, idents):
    """The window of the batch; the batch started, or None (cancelled, or the input edited by hand)."""
    from PySide6.QtWidgets import (QButtonGroup, QDialog, QDialogButtonBox, QDoubleSpinBox, QHBoxLayout, QLabel,
                                   QRadioButton, QVBoxLayout)

    from azimuth import crystal_projects

    panel = getattr(panel, 'panel', panel)  # QeWindow → its QePanel
    if panel.input_edited:
        panel.status.setText(tr('Входной файл изменён вручную — для пакета кристаллов он не годится: «Собрать файл '
                                'заново по настройкам».'))
        return None
    try:
        manifest = _manifest(panel)
    except ValueError as exc:
        panel.status.setText(str(exc))
        return None
    found = {c['id']: c for c in crystal_projects.crystals(manifest)}
    chosen = [found[i] for i in idents if i in found]
    box = QDialog(panel)
    box.setWindowTitle(tr('Пакет кристаллов'))
    layout = QVBoxLayout(box)
    program = 'CP2K' if panel.program == 'cp2k' else 'Quantum ESPRESSO'
    names = ''.join(f'<br>· {c.get("title") or c["id"]}' + (
        tr(' — {} ГПа').format(f'{crystal_projects.pressure(c):g}') if crystal_projects.pressure(c) is not None else '')
        for c in chosen)
    note = QLabel(tr('{}, «{}» — для каждого из {} отмеченных кристаллов по очереди, с этими настройками:').format(
        program, panel.task.currentText(), len(chosen)) + names)
    note.setWordWrap(True)
    layout.addWidget(note)
    group, value = QButtonGroup(box), QDoubleSpinBox()
    value.setRange(0.0, 500.0)
    value.setDecimals(2)
    value.setSuffix(tr(' ГПа'))
    if panel.task.currentData() == CELL_TASK:
        layout.addWidget(QLabel(tr('Давление на ячейку:')))
        none = QRadioButton(tr('без давления'))
        same = QRadioButton(tr('одно для всех'))
        own = QRadioButton(tr('у каждого своё — из его выхода CRYSTAL'))
        own.setEnabled(any(crystal_projects.pressure(c) is not None for c in chosen))
        for k, button in enumerate((none, same, own)):
            group.addButton(button, k)
        (own if own.isEnabled() else none).setChecked(True)
        layout.addWidget(none)
        row = QHBoxLayout()
        row.addWidget(same)
        row.addWidget(value)
        row.addStretch(1)
        layout.addLayout(row)
        layout.addWidget(own)
    buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
    buttons.button(QDialogButtonBox.StandardButton.Ok).setText(tr('Запустить ({})').format(len(chosen)))
    buttons.accepted.connect(box.accept)
    buttons.rejected.connect(box.reject)
    layout.addWidget(buttons)
    if box.exec() != QDialog.DialogCode.Accepted:
        return None
    pressure = {0: None, 1: value.value() or None, 2: OWN}.get(group.checkedId())
    return run(panel, [c['id'] for c in chosen], pressure)


def run(panel, idents, pressure=None):
    panel = getattr(panel, 'panel', panel)  # the window of «Кристалл» (QeWindow) — its panel: the attributes are set there
    batch = CrystalBatch(panel, _manifest(panel), list(idents), pressure)
    batch.start()
    return batch


class CrystalBatch:
    def __init__(self, panel, manifest, idents, pressure=None):
        self.panel, self.manifest, self.left, self.pressure = panel, manifest, list(idents), pressure
        self.total = len(idents)
        self.rows, self.running, self.stopped, self.window = [], False, False, None
        self.current = None
        self.before = (panel.crystal, panel.name)
        self.primitive = panel.primitive.isChecked()
        self.stop_button = None

    def start(self):
        self.running = True
        self.panel.listeners.append(self.heard)
        self.panel.batch = self
        self.next()

    def stop(self):
        self.stopped = True
        self.left = []
        self.panel.stop()

    def next(self):
        from azimuth import crystal_projects
        from modules.compass.chemistry import crystal as cr

        while self.left and not self.stopped:
            ident = self.left.pop(0)
            info = crystal_projects.info(self.manifest, ident)
            title = info.get('title') or ident
            try:
                crystal = cr.parse_cif(crystal_projects.cif_text(self.manifest, ident))
            except (OSError, ValueError) as exc:
                self.rows.append((title, str(exc), '', '', ''))
                continue
            own = crystal_projects.pressure(info)
            self.panel.external = own if self.pressure == OWN else self.pressure
            self.panel.batch_ident, self.panel.batch_name = ident, title
            self.current = (ident, title)
            self.panel.set_crystal_for_batch(crystal, title, self.primitive)
            if self.panel.start() is None:
                self.rows.append((title, self.panel.status.text() or tr('не запущен'), '', '', ''))
                continue
            done = self.total - len(self.left)
            self.panel.status.setText(tr('Пакет: кристалл {} из {} — {} · ').format(done, self.total, title)
                                      + self.panel.status.text())
            return True
        self.finish()
        return False

    def heard(self, event, panel):
        if event != 'end' or not self.running or self.current is None:
            return
        _, title = self.current
        self.current = None
        r = panel.result
        energy = getattr(r, 'energy_hartree', None) if r is not None else None
        ok = r is not None and not getattr(r, 'error', '') and getattr(r, 'done', False) and energy is not None
        pressure = f'{r.pressures[-1]:.2f}' if ok and getattr(r, 'pressures', None) else ''
        volume = ''
        if ok and getattr(r, 'cell', None) is not None:
            import numpy as np

            volume = f'{abs(float(np.linalg.det(np.array(r.cell, dtype=float)))):.2f}'
        status = tr('готово') if ok else (tr('остановлен') if self.stopped else panel.status.text())
        self.rows.append((title, status, f'{energy:.6f}' if ok else '', pressure, volume))
        owner = panel.owner
        if hasattr(owner, 'refresh_project_navigation'):
            owner.refresh_project_navigation()
        QTimer.singleShot(0, self.next)

    def finish(self):
        from modules.compass.actions.qe_results import TableWindow

        if not self.running:
            return
        self.running = False
        if self.heard in self.panel.listeners:
            self.panel.listeners.remove(self.heard)
        self.panel.batch = None
        self.panel.external, self.panel.batch_ident, self.panel.batch_name = None, None, ''
        crystal, name = self.before
        if crystal is not None:
            self.panel.set_crystal(crystal, name)
        lines = [tr('Энергия — полная энергия ячейки, посчитанной программой (примитивной, если так выбрано), в хартри; '
                    'давление — то, что программа насчитала в конце (кбар); объём — ячейки расчёта.')]
        self.window = TableWindow(self.panel, tr('Пакет кристаллов · {} из {}').format(
            sum(1 for r in self.rows if r[2]), self.total),
            [tr('Кристалл'), tr('Итог'), tr('Энергия, Eh'), tr('P, кбар'), tr('V, Å³')], self.rows, lines)
        self.window.show()
        self.panel.status.setText(tr('Пакет кристаллов закончен: посчитано {} из {}.').format(
            sum(1 for r in self.rows if r[2]), self.total))
