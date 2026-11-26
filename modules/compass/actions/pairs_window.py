"""«Кристалл → Энергии пар и каркас (xtb)…»: the interaction energies of a molecule with its neighbours,
the lattice energy and the energy framework on the model (crystal_pairs), as CrystalExplorer.

§1 PURPOSE
    Pair energies and the energy framework of a molecular crystal: single points of GFN2-xTB, a few seconds for a
    crystal of small molecules — quick enough for Compass, in a worker thread.
§2 ALGORITHM
    plan() at once (the shell, the pairs to compute); «Посчитать» runs compute() with run_xtb in a thread (each
    calculation in its folder under the jobs folder of Sextant), the progress through a queued signal; the table and
    the lattice energy when it ends; «Показать каркас» — CrystalTool.show_energy_frame.
§4 SPECIFICATION
    show(studio) -> PairsWindow | None; PairsWindow(parent, crystal, studio, centre): radius, table, summary;
    charges (a table of the kinds of components: formula, number in the cell, charge — guessed by
    crystal_pairs.guess_charges, editable), chosen_charges() -> {formula: q}; the columns E_эл, E_дисп, E_отт,
    E_прочее (the terms of GFN2) when the energy gives them (run_xtb terms=True);
    compute(wait=False) -> started; answer((kind, payload, error)); show_frame() -> bool; energy — the function
    of a molecule (run_xtb by default; replaced in the tests).
§7 TESTS tests/gui/test_gui_files.py::test_the_pair_energies_of_a_crystal (a model energy instead of xtb).
"""

from datetime import datetime
import threading

from PySide6.QtWidgets import (QDialog, QDoubleSpinBox, QHBoxLayout, QHeaderView, QLabel, QSpinBox, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import crystal_pairs, crystal_shell


class PairsWindow(QDialog):
    def __init__(self, parent, crystal, studio=None, centre=None, title=''):
        super().__init__(parent)
        from modules.compass.actions.naming_actions import _Relay

        self.crystal, self.studio, self.centre = crystal, studio, centre or None
        self.plan = self.result = None
        self.busy = False
        self.energy = None  # the energy of a molecule (hartree); None — xtb found when «Посчитать» is pressed
        self.relay = _Relay(self)
        self.relay.done.connect(self.answer)
        self.setWindowTitle(tr('Энергии пар · ') + (title or crystal.title or 'CIF'))
        layout = QVBoxLayout(self)
        note = QLabel(tr('Энергия взаимодействия молекулы с каждым соседом E = E(пара) − E(A) − E(B) в GFN2-xTB при '
                         'геометрии кристалла; энергия решётки ≈ ½ Σ E по соседям в пределах радиуса. '
                         'Точность — порядка 10–20 %. Составляющие — слагаемые GFN2 (электростатика, '
                         'дисперсия, отталкивание, остальное — поляризация и обмен), каждое как разность пары и молекул.'))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        layout.addWidget(note)
        row = QHBoxLayout()
        self.radius = QDoubleSpinBox()
        self.radius.setRange(2.0, 8.0)
        self.radius.setSingleStep(0.2)
        self.radius.setDecimals(1)
        self.radius.setValue(crystal_pairs.RADIUS)
        self.radius.setPrefix(tr('соседи ближе '))
        self.radius.setSuffix(' Å')
        self.radius.setToolTip(tr('Соседняя молекула — с атомом ближе этого расстояния к атому центральной '
                                  '(обычно 3,8 Å)'))
        self.radius.editingFinished.connect(self.prepare)
        row.addWidget(self.radius)
        row.addStretch(1)
        self.go = action_button(tr('Посчитать в xtb'), self.compute, 'play')
        row.addWidget(self.go)
        layout.addLayout(row)
        # the charges of the components (a salt: the ions) — guessed from the formulas, editable
        try:
            self.guessed = crystal_pairs.guess_charges(crystal)
        except ValueError:  # no separate molecules: plan() says so below
            self.guessed = crystal_pairs.Charges({}, {}, {}, {}, True)
        kinds = sorted(self.guessed.counts)
        self.charges = QTableWidget(len(kinds), 3)
        self.charges.setHorizontalHeaderLabels([tr('Компонент'), tr('В ячейке'), tr('Заряд')])
        self.charges.verticalHeader().setVisible(False)
        self.charges.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.charges.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.charge_boxes = {}
        for k, formula in enumerate(kinds):
            self.charges.setItem(k, 0, QTableWidgetItem(formula))
            self.charges.setItem(k, 1, QTableWidgetItem(str(self.guessed.counts[formula])))
            box = QSpinBox()
            box.setRange(-4, 4)
            box.setValue(int(self.guessed.by_formula.get(formula, 0)))
            box.valueChanged.connect(lambda _value: self.prepare())
            self.charges.setCellWidget(k, 2, box)
            self.charge_boxes[formula] = box
        salt = any(self.guessed.by_formula.values()) or not self.guessed.balanced
        self.charges.setVisible(salt)
        self.charges.setMaximumHeight(32 + 28 * max(1, len(kinds)))
        layout.addWidget(self.charges)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 9)
        self.table.setHorizontalHeaderLabels(['№', tr('Код симметрии'), tr('R центров, Å'), tr('Кратчайший контакт'),
                                              tr('E, кДж/моль'), tr('E эл.'), tr('E дисп.'), tr('E отт.'), tr('E прочее')])
        for column, tip in ((5, tr('Электростатика GFN2: изотропная и анизотропная')), (6, tr('Дисперсия D4')),
                            (7, tr('Отталкивание атомов')),
                            (8, tr('Остальное: поляризация, обмен, перенос заряда (E минус три слагаемых)'))):
            self.table.horizontalHeaderItem(column).setToolTip(tip)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        bottom = QHBoxLayout()
        self.frame_button = action_button(tr('Показать каркас на модели'), self.show_frame, 'eye')
        self.frame_button.setEnabled(False)
        bottom.addWidget(self.frame_button)
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.resize(680, 520)
        self.prepare()

    def chosen_charges(self):
        return {formula: box.value() for formula, box in self.charge_boxes.items()}

    def prepare(self):
        try:
            self.plan = crystal_pairs.plan(self.crystal, self.centre, self.radius.value(), charges=self.chosen_charges())
        except ValueError as exc:
            self.plan = None
            self.summary.setText(str(exc))
            self.go.setEnabled(False)
            return None
        self.result = None
        self.frame_button.setEnabled(False)
        self.go.setEnabled(not self.busy)
        p = self.plan
        text = tr('Соседей: {}; расчётов: {} (пары, одинаковые по симметрии, считаются один раз).').format(
            len(p.shell.neighbours), len(p.monomers) + len(p.dimers))
        total = sum(q * self.guessed.counts.get(f, 0) for f, q in self.chosen_charges().items())
        if total:
            text += ' ' + tr('Заряд ячейки {} — проверьте заряды компонентов.').format(f'{total:+d}')
        elif any(self.chosen_charges().values()):
            text += ' ' + tr('Ионы: энергия решётки по ближайшим соседям — только грубая оценка (дальняя '
                             'электростатика не учтена).')
        self.summary.setText(text)
        self.fill()
        return p

    def fill(self):
        p, r = self.plan, self.result
        rows = r.pairs if r is not None else []
        neighbours = p.shell.neighbours if p is not None else ()
        self.table.setRowCount(len(neighbours))
        for k, n in enumerate(neighbours):
            energy = ''
            if rows:
                e = rows[k].energy
                energy = '—' if e is None else f'{e:.1f}'
            distance = f'{rows[k].distance:.2f}' if rows else ''
            terms = rows[k].terms if rows else None
            parts = [f'{terms[key]:.1f}' for key in ('es', 'disp', 'rep', 'rest')] if terms else ['', '', '', '']
            for c, text in enumerate((str(k + 1), n.code, distance, f'{n.pair[0]}···{n.pair[1]} {n.distance:.2f}', energy,
                                      *parts)):
                self.table.setItem(k, c, QTableWidgetItem(text))

    def _energy(self):
        if self.energy is not None:
            return self.energy
        from modules.sextant import runner

        owner = self.studio
        program = runner.find_program('xtb', owner.run_tool.configured_program('xtb')) if hasattr(owner, 'run_tool') else None
        if program is None:
            raise ValueError(tr('xtb не найдена: укажите её в Секстанте («Программа: xtb» → «Указать…») или '
                                'поставьте через «Расчёт → Установить программы для расчёта…».'))
        root = owner.run_tool.jobs_root() / datetime.now().strftime('Pairs_%Y-%m-%d_%H-%M-%S')
        count = [0]

        def energy(molecule, charge=0):
            count[0] += 1
            return crystal_pairs.run_xtb(program, molecule, root / f'{count[0]:03d}', charge=charge, terms=True)

        return energy

    def compute(self):
        if self.busy or self.plan is None:
            return False
        try:
            energy = self._energy()
        except ValueError as exc:
            self.summary.setText(str(exc))
            return False
        self.busy = True
        self.go.setEnabled(False)
        plan, relay = self.plan, self.relay
        self.summary.setText(tr('Считаю в xtb…'))

        def work():
            try:
                result = crystal_pairs.compute(plan, energy, lambda done, total: relay.done.emit(('progress', (done, total), None)))
                relay.done.emit(('result', result, None))
            except Exception as exc:  # xtb missing at run time, a folder that cannot be written: said in the summary
                relay.done.emit(('result', None, exc))

        threading.Thread(target=work, daemon=True).start()
        return True

    def answer(self, message):
        kind, payload, error = message
        if kind == 'progress':
            self.summary.setText(tr('Считаю в xtb: {} из {}…').format(*payload))
            return None
        self.busy = False
        self.go.setEnabled(self.plan is not None)
        if error is not None:
            self.summary.setText(str(error))
            return None
        self.result = payload
        self.fill()
        strongest = min((x for x in payload.pairs if x.energy is not None), key=lambda x: x.energy, default=None)
        text = tr('Энергия решётки ≈ {} кДж/моль (½ Σ по {} соседям).').format(
            f'{payload.lattice:.1f}', len(payload.pairs) - payload.failed)
        if strongest is not None:
            text += ' ' + tr('Самая сильная пара: {} кДж/моль ({}).').format(f'{strongest.energy:.1f}', strongest.neighbour.code)
        if payload.failed:
            text += ' ' + tr('Не посчитано пар: {} — см. вывод xtb в папке расчётов.').format(payload.failed)
        self.summary.setText(text)
        self.frame_button.setEnabled(True)
        return payload

    def show_frame(self):
        if self.result is None or self.studio is None:
            return False
        return bool(self.studio.crystal_tool.show_energy_frame(self.crystal, self.plan, self.result))


def show(studio):
    shown = getattr(studio, 'crystal', None)
    crystal = shown[0] if isinstance(shown, tuple) and shown else shown
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    centre = None
    viewer = getattr(studio, 'viewer', None)
    picked = list(getattr(viewer, 'selected', []) or [])
    if picked and getattr(studio, 'molecule', None) is not None:
        atoms = studio.molecule.atoms
        centre = crystal_shell.locate(crystal, [(atoms[i].x, atoms[i].y, atoms[i].z) for i in picked if i < len(atoms)])
    window = PairsWindow(studio if isinstance(studio, QWidget) else None, crystal, studio, centre)
    studio._pairs_window = window
    window.show()
    return window
