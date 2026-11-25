"""Compass: the «Вращение вокруг связи» window — exact dihedral, turn by an angle, drag, conformer scan.

§1 THEORY modules/compass/chemistry/torsion.py §1.
§2 ALGORITHM The window is opened for a bond (two selected bonded atoms, the bond of a right click, or
               the middle bond of four selected atoms, which then also give the dihedral atoms). It keeps
               the starting geometry and always turns that geometry by the total angle (no build-up of
               rounding); the model shows the preview without history. «Готово» puts the result into
               the history as one step, «Отмена» (or closing) restores the start. Changing the model
               elsewhere while the window is open makes the current model the new start. A left drag
               on an atom of the turning side turns it (TWIST_DEG_PER_PX of the viewer per pixel to the
               right). The scan turns the start by k * step and either opens the frames in the steps
               drawer (a rigid scan: the dihedral and the closest contact per frame) or saves them as
               one XYZ file with several frames (the comment line: dihedral, contact).
§3 APPLICATIONS «Правка → Вращать вокруг связи…», the bond menu of the model.
§4 SPECIFICATION compass_dialogs.torsion(b=None, c=None) (actions/dialog_openers.py) -> TorsionWindow or None; the
window: set_target(deg),
               turn_by(deg), swap_side(), commit(), cancel(), scan_to_drawer(step), scan_text(step).
§5 PROCEDURES below.
§6 NOTES No relaxation: the scan is a rigid torsion scan for a first look (a relaxed scan needs a
               calculation: Sextant, ORCA %geom Scan).
§7 TESTS tests/compass/test_torsion.py (geometry); tests/test_gui.py::test_rotation_about_a_bond_window.
§8' ROBUSTNESS a ring bond or atoms that are not bonded: a message, no window; an undefined dihedral (a
               linear end): only turns by an angle.
"""

from dataclasses import replace
from types import SimpleNamespace

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSlider,
    QVBoxLayout,
)

from modules.compass.chemistry import torsion
from azimuth.i18n import tr
from azimuth.ui import action_button

STEPS = (5, 10, 15, 30, 45, 60, 90, 120, 180)


class TorsionWindow(QDialog):
    def __init__(self, owner, b, c, a=None, d=None):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(tr('Вращение вокруг связи'))
        self.setWindowFlag(Qt.WindowType.Tool, True)
        self.b, self.c = b, c
        ra, rd = torsion.reference(owner.molecule, b, c)
        self.a = a if a is not None else ra
        self.d = d if d is not None else rd
        self.moving = c
        self.start = owner.molecule
        self.angle = 0.0  # the total turn of the start shown now
        self._shown = owner.molecule
        self._busy = False
        torsion.side(self.start, b, c, self.moving)  # a ring bond is refused here
        layout = QVBoxLayout(self)
        self.head = QLabel()
        self.head.setWordWrap(True)
        layout.addWidget(self.head)
        swap = QPushButton(tr('Вращать другую сторону'))
        swap.clicked.connect(self.swap_side)
        layout.addWidget(swap, 0, Qt.AlignmentFlag.AlignLeft)
        grid = QGridLayout()
        self.dihedral_label = QLabel()
        grid.addWidget(self.dihedral_label, 0, 0)
        self.value = QDoubleSpinBox()
        self.value.setRange(-180.0, 180.0)
        self.value.setDecimals(1)
        self.value.setSingleStep(1.0)
        self.value.setWrapping(True)
        self.value.setSuffix(' °')
        self.value.valueChanged.connect(lambda v: self.set_target(v) if not self._busy else None)
        grid.addWidget(self.value, 0, 1)
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(-1800, 1800)
        self.slider.valueChanged.connect(lambda v: self.set_target(v / 10) if not self._busy else None)
        grid.addWidget(self.slider, 1, 0, 1, 2)
        grid.addWidget(QLabel(tr('Повернуть на')), 2, 0)
        turn_row = QHBoxLayout()
        self.step = QDoubleSpinBox()
        self.step.setRange(0.1, 180.0)
        self.step.setDecimals(1)
        self.step.setValue(15.0)
        self.step.setSuffix(' °')
        turn_row.addWidget(self.step)
        for sign, text in ((-1, '−'), (1, '+')):
            button = QPushButton(text)
            button.setFixedWidth(34)
            button.clicked.connect(lambda checked=False, s=sign: self.turn_by(s * self.step.value()))
            turn_row.addWidget(button)
        grid.addLayout(turn_row, 2, 1)
        layout.addLayout(grid)
        hint = QLabel(tr('Можно тянуть мышью любой атом вращаемой стороны влево-вправо.'))
        hint.setWordWrap(True)
        hint.setObjectName('muted')
        layout.addWidget(hint)
        self.contact_label = QLabel()
        layout.addWidget(self.contact_label)
        scan_row = QHBoxLayout()
        scan_row.addWidget(QLabel(tr('Перебор, шаг')))
        self.scan_step = QComboBox()
        for s in STEPS:
            self.scan_step.addItem(f'{s}°', s)
        self.scan_step.setCurrentIndex(STEPS.index(30))
        scan_row.addWidget(self.scan_step)
        to_drawer = action_button(tr('В панель шагов'), lambda: self.scan_to_drawer(self.scan_step.currentData()), 'menu')
        scan_row.addWidget(to_drawer)
        save = action_button(tr('Сохранить XYZ…'), self.save_scan, 'save')
        scan_row.addWidget(save)
        layout.addLayout(scan_row)
        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton(tr('Отмена'))
        cancel.clicked.connect(self.cancel)
        done = QPushButton(tr('Готово'))
        done.setDefault(True)
        done.clicked.connect(self.commit)
        buttons.addWidget(cancel)
        buttons.addWidget(done)
        layout.addLayout(buttons)
        self.rejected.connect(self._restore)
        self._arm()
        self.refresh()

    # -- state --------------------------------------------------------------------------------------
    SAME = 1e-6  # A: the table keeps 8 decimals, so the model read back differs by up to 5e-9 A

    def _same(self, m):
        s = self._shown
        return len(m.atoms) == len(s.atoms) and all(
            p.symbol == q.symbol and max(abs(p.position[k] - q.position[k]) for k in range(3)) < self.SAME
            for p, q in zip(m.atoms, s.atoms)
        )

    def _sync(self):
        """If the model was changed elsewhere, it becomes the new start."""
        if not self._same(self.owner.molecule):
            self.start = self.owner.molecule
            self.angle = 0.0
            self._shown = self.start
            self._arm()

    def _arm(self):
        viewer = self.owner.viewer
        viewer.twist = self._drag
        viewer.twist_group = tuple(torsion.side(self.start, self.b, self.c, self.moving))

    def _disarm(self):
        viewer = self.owner.viewer
        viewer.twist = None
        viewer.twist_group = ()

    def name(self, i):
        return self.start.atoms[i].symbol + str(i + 1)

    def defined(self):
        if self.a is None or self.d is None:
            return False
        try:
            torsion.dihedral(self.start, self.a, self.b, self.c, self.d)
            return True
        except ValueError:
            return False

    def current_dihedral(self):
        return torsion.dihedral(self._shown, self.a, self.b, self.c, self.d) if self.defined() else None

    def refresh(self):
        group = torsion.side(self.start, self.b, self.c, self.moving)
        self.head.setText(
            tr('Связь ')
            + self.name(self.b)
            + '–'
            + self.name(self.c)
            + tr(' · вращается сторона ')
            + self.name(self.moving)
            + tr(f' (атомов: {len(group)})')
        )
        value = self.current_dihedral()
        self._busy = True
        if value is None:
            self.dihedral_label.setText(tr('Двугранный угол не определён'))
            self.value.setEnabled(False)
            self.slider.setEnabled(False)
        else:
            self.dihedral_label.setText(
                tr('Двугранный угол ') + '–'.join(self.name(i) for i in (self.a, self.b, self.c, self.d))
            )
            self.value.setValue(value)
            self.slider.setValue(round(value * 10))
        self._busy = False
        found = torsion.contact(self._shown, group)
        self.contact_label.setText(
            tr(f'Ближайший контакт сторон: {found[0]:.2f} Å ({self.name(found[1])}···{self.name(found[2])})')
            if found
            else ''
        )

    def show_turn(self, angle):
        self._sync()
        self.angle = angle
        molecule = torsion.turn(self.start, self.b, self.c, self.moving, angle) if angle else self.start
        self._shown = molecule
        self.owner.trajectory_tool.show_molecule(molecule)
        self.owner.viewer.update()
        self.refresh()

    # -- actions ------------------------------------------------------------------------------------
    def set_target(self, target):
        if not self.defined():
            return
        self._sync()
        try:
            molecule = torsion.set_dihedral(self.start, self.a, self.b, self.c, self.d, self.moving, target)
        except ValueError as exc:
            self.owner.error(exc)
            return
        start = torsion.dihedral(self.start, self.a, self.b, self.c, self.d)
        self.angle = (target - start + 180.0) % 360.0 - 180.0
        self._shown = molecule
        self.owner.trajectory_tool.show_molecule(molecule)
        self.refresh()

    def turn_by(self, degrees):
        self.show_turn(self.angle + degrees)

    def _drag(self, stage, degrees):
        if stage == 'start':
            self._drag_from = self.angle
        elif stage in ('move', 'end'):
            self.show_turn(getattr(self, '_drag_from', self.angle) + degrees)

    def swap_side(self):
        """Turn the other side (the same relative turn; the other side moves on the screen)."""
        self._sync()
        other = self.b if self.moving == self.c else self.c
        try:
            torsion.side(self.start, self.b, self.c, other)
        except ValueError as exc:
            self.owner.error(exc)
            return
        current = self._shown
        self.moving = other
        self.start = current  # keep what is shown, from now on the other side turns
        self.angle = 0.0
        self._arm()
        self.refresh()

    def frames(self, step):
        return torsion.scan(self.start, self.b, self.c, self.moving, float(step), self.a, self.d)

    def scan_text(self, step):
        parts = []
        for turned, value, found, molecule in self.frames(step):
            title = tr(f'поворот {turned:.1f}°')
            if value is not None:
                title += tr(f'; двугранный угол {value:.1f}°')
            if found:
                title += tr(f'; ближайший контакт {found[0]:.2f} Å')
            parts.append(replace(molecule, title=title).xyz().rstrip('\n'))
        return '\n'.join(parts) + '\n'

    def save_scan(self):
        step = self.scan_step.currentData()
        try:
            self.owner.save_text(
                tr('Сохранить перебор конформеров'), 'XYZ (*.xyz)', self.scan_text(step), f'torsion-scan-{step}.xyz'
            )
        except (ValueError, OSError) as exc:
            self.owner.error(exc)

    def scan_to_drawer(self, step):
        """The frames in the steps drawer of Compass (a rigid scan; energies are not known)."""
        from modules.spectrum.readers.orca_scan import Coordinate, Point, Scan

        try:
            frames = self.frames(step)
        except ValueError as exc:
            self.owner.error(exc)
            return None
        coordinate = (
            Coordinate('dihedral', (self.a, self.b, self.c, self.d))
            if self.defined()
            else Coordinate('parameter', (), tr('поворот, °'))
        )
        points = tuple(
            Point(k + 1, ((value if value is not None else turned),), None, replace(m, title=''))
            for k, (turned, value, _, m) in enumerate(frames)
        )
        scan = Scan('rigid', (coordinate,), points)
        self.cancel()
        self.owner.trajectory_tool.load_trajectory(SimpleNamespace(steps=(), scan=scan, initial_geometry=None), tr('перебор вокруг связи'))
        self.owner.opening_tool.show_trajectory_drawer()
        return scan

    def commit(self):
        self._disarm()
        result = self._shown
        start = self.start
        self.owner.trajectory_tool.show_molecule(start)
        if result.atoms != start.atoms:
            self.owner.load_molecule(result, preserve_view=True)
        self._done = True
        self.accept()

    def cancel(self):
        self.reject()

    def _restore(self):
        self._disarm()
        if not getattr(self, '_done', False):
            self.owner.trajectory_tool.show_molecule(self.start)
            self.owner.viewer.update()
