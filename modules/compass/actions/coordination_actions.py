"""Compass: «Правка → Геометрия → Координационный центр…» — a metal and its ligands in an ideal polyhedron
(modules/compass/chemistry/coordination.py). The structure replaces the one shown (after confirm_replace, as the
peptide); the charge of the complex and the lowest multiplicity of its electrons go to the fields of the tab; the
clashes of a crowded polyhedron are said in the message, the structure is still built."""

from dataclasses import dataclass
from typing import Callable

from PySide6.QtGui import QAction

from azimuth.i18n import tr


@dataclass(frozen=True)
class CoordinationPort:
    parent: object  # of the action and the dialog
    error: Callable[[Exception], None]
    confirm_replace: Callable[[], bool]
    edit_structure: Callable[[object, str], None]
    set_state: Callable[[int, int], None]  # charge, multiplicity


class CoordinationTool:
    def __init__(self, port):
        self.port = port
        self.action = QAction(tr('Координационный центр…'), port.parent)
        self.action.setToolTip(tr('Металл и лиганды в идеальном многограннике: октаэдр, тетраэдр, плоский квадрат, '
                                  'бипирамиды; M–L по ковалентным радиусам'))
        self.action.triggered.connect(lambda *_: self.dialog())

    def dialog(self, values=None):
        """values = (metal, geometry key, ligands text, oxidation state) without the window — the tests."""
        from modules.compass.chemistry import coordination

        if values is None:
            values = self._ask(coordination)
            if values is None:
                return None
        if not self.port.confirm_replace():
            return None
        try:
            built = coordination.build(*values)
        except ValueError as exc:
            self.port.error(exc)
            return None
        molecule = built.molecule
        electrons = molecule.electrons(built.charge)
        multiplicity = 1 if electrons % 2 == 0 else 2
        sign = f'{built.charge:+d}' if built.charge else '0'
        message = tr('{}: {}, заряд {}, мультиплетность {} (наименьшая; высокоспиновое состояние задайте сами). '
                     'Длины M–L — по ковалентным радиусам, геометрию стоит оптимизировать.').format(
            molecule.title, tr(coordination.GEOMETRIES[values[1]][0]), sign, multiplicity)
        if built.clashes:
            message += ' ' + tr('Лигандам тесно: {} пар атомов ближе 0,7 суммы ван-дер-ваальсовых радиусов.').format(
                len(built.clashes))
        self.port.edit_structure(molecule, message)
        # after the structure — loading it makes Sextant guess the state of the new formula (advice.guess_state:
        # [Co(NH3)5Cl] gave 5 and 2 over the 2 and 1 set before); set now, the formula is the one guessed for and stays
        self.port.set_state(built.charge, multiplicity)
        return built

    def _ask(self, coordination):
        from PySide6.QtWidgets import QComboBox, QDialog, QDialogButtonBox, QFormLayout, QLabel, QLineEdit, QSpinBox

        box = QDialog(self.port.parent)
        box.setWindowTitle(tr('Координационный центр'))
        form = QFormLayout(box)
        metal = QLineEdit('Fe')
        form.addRow(tr('Металл:'), metal)
        state = QSpinBox()
        state.setRange(-4, 8)
        state.setValue(2)
        form.addRow(tr('Степень окисления:'), state)
        shape = QComboBox()
        for key, (title, directions) in coordination.GEOMETRIES.items():
            shape.addItem(f'{tr(title)} ({len(directions)})', key)
        shape.setCurrentIndex(list(coordination.GEOMETRIES).index('octahedral'))
        form.addRow(tr('Геометрия:'), shape)
        ligands = QLineEdit('H2O')
        ligands.setToolTip(tr('Один лиганд на все места, список через запятую или «4 Cl, 2 NH3». Есть: ')
                           + ', '.join(coordination.LIGANDS))
        form.addRow(tr('Лиганды:'), ligands)
        note = QLabel(tr('Порядок мест: в бипирамидах сначала два аксиальных, в квадратной пирамиде сначала '
                         'апикальное, затем экваториальные. Есть: ') + ', '.join(coordination.LIGANDS) + '.')
        note.setWordWrap(True)
        form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(box.accept)
        buttons.rejected.connect(box.reject)
        form.addRow(buttons)
        if box.exec() != QDialog.DialogCode.Accepted:
            return None
        return metal.text(), shape.currentData(), ligands.text(), state.value()
