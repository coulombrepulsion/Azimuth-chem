"""BatchDialog: the window «Очередь расчётов» — which structures go into a queue, and «Комплексы с ионом».

Split off modules/sextant/batch_actions.py (0.222.29).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QSpinBox,
    QVBoxLayout,
)
from azimuth.i18n import tr
from modules.sextant import batch as batches


class BatchDialog(QDialog):
    """The choice of the structures of the queue."""

    def __init__(self, parent, title, rows, chosen=None, binding=None, flat=()):
        """Binding — offer «Комплексы с ионом» (a set of structures, not conformers): None, or
        {'orca': BSSE possible, 'chosen': the binding chosen before}; flat — the rows that are 2D drawings."""
        super().__init__(parent)
        self.setWindowTitle(tr('Очередь расчётов'))
        column = QVBoxLayout(self)
        head = QLabel(title)
        head.setObjectName('cardtitle')
        column.addWidget(head)
        note = QLabel(tr(f'Одни и те же настройки Секстанта для всех; расчёты идут по одному. По умолчанию — до '
                         f'{batches.WINDOW:g} ккал/моль от самого низкого.'))
        note.setObjectName('subtitle')
        note.setWordWrap(True)
        column.addWidget(note)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Сколько:')))
        self.count = QSpinBox()
        self.count.setRange(1, max(1, len(rows)))
        self.count.setValue(batches.default_count([delta for _, delta in rows]))
        self.count.setToolTip(tr('Отметить столько самых низких'))
        self.count.setAlignment(Qt.AlignmentFlag.AlignCenter)
        row.addWidget(self.count)
        self.chosen_label = QLabel()
        self.chosen_label.setObjectName('subtitle')
        row.addWidget(self.chosen_label, 1)
        column.addLayout(row)
        self.listing = QListWidget()
        for name, delta in rows:
            item = QListWidgetItem(name + ('' if delta is None else f'   ΔE = {delta:.2f} ' + tr('ккал/моль')))
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.listing.addItem(item)
        column.addWidget(self.listing, 1)
        self.binding_box = None
        if binding is not None:
            self._binding_part(column, binding, flat)
        buttons = QDialogButtonBox()
        # the dialog only chooses; the queue is started by «Запустить очередь» of the card of the calculation
        self.start_button = buttons.addButton(tr('Выбрать для очереди'), QDialogButtonBox.ButtonRole.AcceptRole)
        self.start_button.setObjectName('primary')
        buttons.addButton(tr('Отмена'), QDialogButtonBox.ButtonRole.RejectRole)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        column.addWidget(buttons)
        self.count.valueChanged.connect(self.take_first)
        self.listing.itemChanged.connect(lambda *a: self.tell())
        self.take_first(self.count.value())
        if chosen is not None:  # «Изменить…»: the choice made before
            self.listing.blockSignals(True)
            for k in range(self.listing.count()):
                self.listing.item(k).setCheckState(Qt.CheckState.Checked if k in chosen else Qt.CheckState.Unchecked)
            self.listing.blockSignals(False)
            self.tell()
        self.resize(460, 480)

    def _binding_part(self, column, binding, flat):
        """«Комплексы с ионом» — the ion, each ligand and its complex in one queue (modules/sextant/binding.py)."""
        from PySide6.QtWidgets import QCheckBox, QComboBox

        from modules.sextant import binding as binding_

        self.binding_box = QCheckBox(tr('Комплексы с ионом: ион, каждый лиганд и его комплекс, энергии связывания'))
        self.binding_box.setToolTip(tr('Ион ставится в лиганд по донорам (O, N, S …), комплекс оптимизируется после '
                                       'лиганда — на его геометрии; в конце — таблица ΔE, ΔE(CP), ΔG связывания'))
        column.addWidget(self.binding_box)
        row = QHBoxLayout()
        self.ion = QComboBox()
        for symbol, (charge, d0) in binding_.IONS.items():
            self.ion.addItem(f'{binding_.ion_name(symbol, charge)}  ·  d(M–O) ≈ {d0:.2f} Å', symbol)
        self.bsse = QCheckBox(tr('Поправка BSSE (противовес, ORCA)'))
        self.bsse.setToolTip(tr('Ещё три расчёта энергии на каждый комплекс: лиганд при геометрии комплекса, лиганд и '
                                'ион с атомами-призраками партнёра (Бойс — Бернарди)'))
        self.bsse.setEnabled(bool(binding.get('orca')))
        row.addWidget(QLabel(tr('Ион:')))
        row.addWidget(self.ion, 1)
        row.addWidget(self.bsse)
        column.addLayout(row)
        self.flat_note = QLabel()
        self.flat_note.setObjectName('subtitle')
        self.flat_note.setWordWrap(True)
        self.flat_rows = set(flat or ())
        column.addWidget(self.flat_note)
        before = binding.get('chosen')
        if before:
            self.binding_box.setChecked(True)
            self.ion.setCurrentIndex(max(0, self.ion.findData(before.get('ion'))))
            self.bsse.setChecked(bool(before.get('bsse')) and self.bsse.isEnabled())
        for item in (self.ion, self.bsse):
            item.setEnabled(item.isEnabled() and self.binding_box.isChecked())
        self.binding_box.toggled.connect(lambda on: (self.ion.setEnabled(on),
                                                     self.bsse.setEnabled(on and bool(binding.get('orca'))), self.tell()))

    def binding(self):
        """{'ion', 'charge', 'bsse'} when «Комплексы с ионом» is chosen, else None."""
        if self.binding_box is None or not self.binding_box.isChecked():
            return None
        from modules.sextant.binding import IONS

        symbol = self.ion.currentData()
        return {'ion': symbol, 'charge': IONS[symbol][0], 'bsse': self.bsse.isChecked() and self.bsse.isEnabled()}

    def take_first(self, n):
        self.listing.blockSignals(True)
        for k in range(self.listing.count()):
            self.listing.item(k).setCheckState(Qt.CheckState.Checked if k < n else Qt.CheckState.Unchecked)
        self.listing.blockSignals(False)
        self.tell()

    def chosen(self):
        return [k for k in range(self.listing.count()) if self.listing.item(k).checkState() == Qt.CheckState.Checked]

    def tell(self):
        n = len(self.chosen())
        self.chosen_label.setText(tr(f'выбрано: {n} из {self.listing.count()}'))
        self.start_button.setEnabled(n > 0)
        if self.binding_box is not None:
            flat = sum(1 for k in self.chosen() if k in self.flat_rows)
            self.flat_note.setText(tr(f'Плоских (2D) среди выбранных: {flat} — ион в плоский рисунок ставится плохо: '
                                      'сначала «Геометрия → Сделать 3D (RDKit)» или поиск конформеров в Настройках.')
                                   if flat and self.binding_box.isChecked() else '')
