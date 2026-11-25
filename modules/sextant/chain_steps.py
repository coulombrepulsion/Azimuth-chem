"""The steps of a chain in «Постановка задачи» of Sextant, each with its own method and basis set.

§1 PURPOSE
    A chain (modules/sextant/chain.py) chosen in the list «Задача» shows its steps under it: the first one is
    computed with the settings of the form, each next one may have its own method and basis set (an optimization in
    B3LYP/def2-SVP, then TD-DFT in CAM-B3LYP/def2-TZVP). «Запустить расчёт» starts the whole chain
    (RunTool.run_calculation → BatchTool.start_chain with overrides()).
§2 RULES
    1. The items of the list «Задача» of a chain: KEY_ROLE — the task of its first step (the rest of the form and the
       input file shown are those of the first step), CHAIN_ROLE — the key of the chain.
    2. A step not touched by the user follows the form (and the change of its preset: «+» of a basis — the larger
       one of the form's); a step whose method or basis was chosen keeps it until another chain is chosen.
§4 SPECIFICATION
    CHAIN_ROLE; ChainSteps(window): show_for(key), sync() (the form changed), overrides(key) -> [dict] | None
    (per step: {'method', 'basis'} that differ from the form, or the preset's), rows -> [(task, method, basis)].
§7 TESTS
    tests/gui/test_gui_sextant.py::test_a_chain_chosen_in_the_list_of_tasks.
"""

from PySide6.QtWidgets import QComboBox, QGridLayout, QLabel, QSizePolicy, QWidget

from azimuth.i18n import tr

CHAIN_ROLE = 0x0100 + 78  # Qt.UserRole + 78: the key of a chain in the list «Задача» (KEY_ROLE is + 77)


def _value(combo):
    """The key of the item whose text is shown (an item chosen or typed), else the text typed (a basis of one's own)."""
    text = combo.currentText().strip()
    index = combo.findText(text)
    data = combo.itemData(index) if index >= 0 else None
    return data if isinstance(data, str) and data else text


class ChainSteps(QWidget):
    def __init__(self, window):
        super().__init__()
        self.w = window
        self.key = None
        self.rows = []  # [(task, method combo | None, basis combo | None, changes of the preset)]
        self.touched = set()  # (row, 'method' | 'basis') chosen by the user
        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(0, 2, 0, 6)
        self.grid.setHorizontalSpacing(8)
        self.grid.setVerticalSpacing(6)
        self.hide()

    def show_for(self, key):
        """The steps of the chain key (None — none: hidden)."""
        if key != self.key:
            self.touched = set()
        self.key = key
        while self.grid.count():
            item = self.grid.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.hide()
                widget.deleteLater()
        self.rows = []
        if key is None:
            self.hide()
            return
        from modules.sextant import chain

        try:
            calc = self.w.calculation()
        except ValueError:
            return
        head = QLabel(tr('Шаги цепочки · у каждого свои метод и базис; входной файл ниже — первого шага'))
        head.setObjectName('subtitle')
        head.setWordWrap(True)
        self.grid.addWidget(head, 0, 0, 1, 3)
        for k, (_, task, changes) in enumerate(chain.steps(key, calc), start=1):
            title = QLabel(f'{k}. {tr(task)}')
            title.setWordWrap(True)
            title.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
            self.grid.addWidget(title, k, 0)
            if k == 1:
                same = QLabel(tr('по настройкам выше'))
                same.setObjectName('subtitle')
                self.grid.addWidget(same, k, 1, 1, 2)
                self.rows.append((task, None, None, changes))
                continue
            method, basis = self._combo(self.w.method, k, 'method'), self._combo(self.w.basis, k, 'basis')
            self.grid.addWidget(method, k, 1)
            self.grid.addWidget(basis, k, 2)
            self.rows.append((task, method, basis, changes))
        self.grid.setColumnStretch(0, 3)
        self.grid.setColumnStretch(1, 2)
        self.grid.setColumnStretch(2, 2)
        self.sync()
        self.show()

    def _combo(self, source, row, field):
        box = QComboBox()
        box.setEditable(True)
        box.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        for i in range(source.count()):
            box.addItem(source.itemText(i), source.itemData(i))
        box.setMinimumContentsLength(6)
        box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        box.setToolTip(tr('Метод этого шага') if field == 'method' else tr('Базис этого шага'))
        box.activated.connect(lambda *_: self.touched.add((row, field)))
        box.lineEdit().textEdited.connect(lambda *_: self.touched.add((row, field)))
        return box

    def sync(self):
        """The steps not touched follow the form: its method and basis, or the preset's change of them."""
        if not self.rows:
            return
        from modules.sextant import chain

        try:
            calc = self.w.calculation()
        except ValueError:
            return
        filled = next(((m, b) for _, m, b, _ in self.rows if m is not None), None)
        if filled is not None and (filled[0].count() != self.w.method.count() or filled[1].count() != self.w.basis.count()):
            self.show_for(self.key)  # another program: its methods and basis sets in the lists of the steps
            return
        presets = chain.steps(self.key, calc)
        for k, (task, method, basis, _) in enumerate(self.rows, start=1):
            if method is None:
                continue
            changes = presets[k - 1][2] if k - 1 < len(presets) else {}
            for field, box in (('method', method), ('basis', basis)):
                if (k, field) in self.touched:
                    continue
                value = changes.get(field, getattr(calc, field))
                index = box.findData(value)
                if index < 0:
                    index = box.findText(value)
                blocked = box.blockSignals(True)
                if index >= 0:
                    box.setCurrentIndex(index)
                else:
                    box.setEditText(value)
                box.blockSignals(blocked)

    def overrides(self, key):
        """[{'method', 'basis'}] of every step for chain.items (the first: {}), or None (another chain shown)."""
        if key != self.key or not self.rows:
            return None
        out = []
        for task, method, basis, _ in self.rows:
            if method is None:
                out.append({})
                continue
            out.append({'method': _value(method), 'basis': _value(basis)})
        return out

    def table(self):
        """[(task, method, basis)] as shown (the first step: the form's)."""
        try:
            calc = self.w.calculation()
        except ValueError:
            return []
        return [(task, calc.method, calc.basis) if method is None else (task, _value(method), _value(basis))
                for task, method, basis, _ in self.rows]
