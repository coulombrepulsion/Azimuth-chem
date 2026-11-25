"""The molecule of a calculation in Sextant: the charge and multiplicity following its structure, a basis set of an
element, the fragments of CDA and of the interaction energy, the structure and constraints that go to the program.
Methods of SextantWorkspace (self is the window), kept here to make workspace.py shorter.

Split off modules/sextant/workspace.py (0.222.30).
"""

from PySide6.QtWidgets import QComboBox, QFormLayout
from azimuth.core import BASIS_TABLE, bases_for
from modules.sextant import advice
from azimuth.i18n import tr


def follow_molecule_state(self, molecule):
    """Charge and multiplicity follow the structure when its composition changes; a change by hand stays and
    gets a remark with what the structure suggests."""
    charge, multiplicity, note = advice.guess_state(molecule)
    if molecule.formula != self._state_formula:
        self._state_formula = molecule.formula
        for box, value in ((self.charge, charge), (self.spin, multiplicity)):
            box.blockSignals(True)
            box.setValue(value)
            box.blockSignals(False)
    if (self.charge.value(), self.spin.value()) != (charge, multiplicity) and molecule.atoms:
        self.state_note.setText(tr(f'Изменено вручную; по структуре — заряд {charge}, мультиплетность {multiplicity}.'))
        self.state_note.show()
    elif note:
        self.state_note.setText(tr(f'По структуре: {note}.'))
        self.state_note.show()
    else:
        self.state_note.hide()
    self.molecule_state_changed()


def molecule_state_changed(self):
    """Charge or multiplicity changed (by hand or with the structure): the summaries that show them."""
    if hasattr(self, 'update_calc_card'):
        self.update_calc_card()
    self.update_options_summary()


def add_element_basis(self, symbol=None, basis=None):
    """An element of the molecule and its own basis set — asked in a small window, or given (tests); the
    field rewritten in order of the atomic numbers. Returns the new text, or None when cancelled."""
    from azimuth.core import Z, element_basis_text, element_bases

    try:
        own = element_bases(self.element_basis.text())
    except ValueError:
        own = {}
    if symbol is None or basis is None:
        from PySide6.QtWidgets import QDialog, QDialogButtonBox

        symbols = sorted({a.symbol for a in self.coordinate_tool.table_molecule().atoms if a.symbol != 'X'}, key=Z.get)
        if not symbols:
            self.notify(tr('Добавьте атомы в Компасе — потом выберите базисы элементов.'), 6000)
            return None
        dialog = QDialog(self)
        dialog.setWindowTitle(tr('Базис элемента'))
        form = QFormLayout(dialog)
        element, chosen = QComboBox(), QComboBox()
        element.addItems(symbols)
        kind = self.program_kind()
        for key in (bases_for(kind) if kind in ('orca', 'gaussian', 'psi4') else BASIS_TABLE):
            chosen.addItem(key, key)
        chosen.setCurrentIndex(max(0, chosen.findData(own.get(symbols[0], self.basis.currentData()))))
        form.addRow(tr('Элемент'), element)
        form.addRow(tr('Базис'), chosen)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if not dialog.exec():
            return None
        symbol, basis = element.currentText(), chosen.currentData()
    own[symbol] = basis
    text = element_basis_text(own)
    self.element_basis.setText(text)
    return text


def cda_from_selection(self):
    """The atoms selected in Compass as fragment 1 of CDA (in the numbering of the calculation: without the
    dummy atoms); the text written, or None when nothing is selected."""
    from azimuth import atom_labels

    selected = sorted(getattr(getattr(self, 'viewer', None), 'selected', ()) or ())
    if not selected:
        self.notify(tr('Выделите в Компасе атомы фрагмента 1 (донора) и нажмите снова.'), 8000)
        return None
    atoms = self.coordinate_tool.table_molecule().atoms
    numbering, k = {}, 0
    for i, atom in enumerate(atoms):
        if atom.symbol != 'X':
            k += 1
            numbering[i] = k
    symbols = [a.symbol for a in atoms if a.symbol != 'X']
    text = atom_labels.text([numbering[i] for i in selected if i in numbering], symbols)  # «N1–H4»
    self.cda_atoms.setText(text)
    return text


def cda_note(self):
    """What the queue of CDA will be — or what is wrong with the fragments."""
    from modules.spectrum.wavefunction import multiwfn_cda

    try:
        found = multiwfn_cda.plan(self.calculation_molecule(), self.calculation())
    except ValueError as exc:
        return str(exc)
    (_, one, q1, m1), (_, two, q2, m2) = found['parts'][1], found['parts'][2]
    return tr(f'Три расчёта одной геометрии очередью: комплекс, фрагмент 1 — {one.formula} (заряд {q1:+d}, '
              f'2S+1 = {m1}), фрагмент 2 — {two.formula}, остальные атомы (заряд {q2:+d}, 2S+1 = {m2}); затем '
              'Multiwfn: донирование d, обратное донирование b, отталкивание r.')


def interaction_note(self):
    """What the queue of the interaction energy will be — or what is wrong with the structure."""
    from modules.sextant import interaction

    try:
        return interaction.note(self.calculation_molecule(), self.calculation())
    except ValueError as exc:
        return str(exc)


def calculation_molecule(self):
    """The structure that goes to a program — without the dummy atoms X (they have no nucleus)."""
    from azimuth.core import without_dummies

    return without_dummies(self.coordinate_tool.table_molecule())


def calculation_constraints(self):
    """The constraints in the numbering of calculation_molecule(); those with a dummy atom are left out."""
    fixed = tuple(getattr(self, 'constraints', ()) or ())
    mol = self.coordinate_tool.table_molecule()
    dummies = [k for k, a in enumerate(mol.atoms) if a.symbol == 'X']
    if not dummies:
        return fixed
    new = {}
    for k, a in enumerate(mol.atoms):
        if a.symbol != 'X':
            new[k] = len(new)
    return tuple((kind, tuple(new[i] for i in atoms)) for kind, atoms in fixed if all(i in new for i in atoms))
