"""«Среднее по конформерам…» of the NMR tab: the shieldings of a flexible molecule averaged by the Boltzmann shares.

§1 PURPOSE
    The conformers of a flexible molecule exchange faster than the spectrometer measures, so a nucleus gives one
    signal at the average of its shieldings, each conformer with its share. The window takes the NMR results of the
    conformers (the same molecule, the same order of the atoms, the same level), shows their electronic energies and
    proposes the shares by them; the column «ΔG, кДж/моль» can be typed over with the free energies of the
    calculations with frequencies («Инструменты → Энергии из нескольких файлов» gives them) — the shares follow.
§4 SPECIFICATION
    NMRConformersDialog(owner, read=None) — fill(paths) -> rows | None (the reason in the note), table (file, E, ΔG —
    editable, share), temperature; shares() -> [p] | None; average() -> (tuple of Shielding, the outputs, the shares)
    and the signal built(object) with the same; read(path) -> (output of read_any, text).
    ensemble.weighted_shieldings does the sum.
§7 TESTS
    tests/gui/test_gui_spectrum.py::test_nmr_conformers_dialog.
"""

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QDoubleSpinBox, QFileDialog, QHBoxLayout, QLabel, QTableWidgetItem, QVBoxLayout

from azimuth.i18n import tr
from azimuth.ui import button, label
from modules.spectrum.views.tools_view import _table

KJ = 2625.499639  # kJ/mol per hartree
HEADERS = ('Файл', 'E, хартри', 'ΔG, кДж/моль', 'Доля, %')


def _read(path):
    from modules.spectrum.readers.outputs import read_any

    text = Path(path).read_text(encoding='utf-8', errors='replace')
    return read_any(text, str(path)), text


def _energy(output):
    """The electronic energy of a result, hartree, or None."""
    final = getattr(output, 'final_energy', None)
    if final:
        return float(final[1])
    energies = getattr(output, 'energies', None)
    return float(energies[-1]) if energies else None


class NMRConformersDialog(QDialog):
    built = Signal(object)

    def __init__(self, owner, read=None):
        super().__init__(owner)
        self.setWindowTitle(tr('ЯМР: среднее по конформерам'))
        self.read = read or _read
        self.paths, self.outputs, self.texts = [], [], []
        lay = QVBoxLayout(self)
        hint = label(tr('Выберите расчёты ЯМР конформеров одной молекулы (один метод, один порядок атомов). Доли '
                        'предложены по электронной энергии этих расчётов. Точнее — по свободной энергии: впишите в '
                        'столбец «ΔG» значения из расчётов с частотами.'), 'subtitle')
        hint.setWordWrap(True)
        lay.addWidget(hint)
        top = QHBoxLayout()
        top.addWidget(button(tr('Выбрать расчёты ЯМР…'), lambda: self.choose()))
        top.addWidget(QLabel(tr('Температура')))
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(1, 5000)
        self.temperature.setDecimals(2)
        self.temperature.setSuffix(' K')
        self.temperature.setValue(298.15)
        self.temperature.valueChanged.connect(lambda *_: self.update_shares())
        top.addWidget(self.temperature)
        top.addStretch(1)
        lay.addLayout(top)
        self.table = _table(HEADERS)
        self.table.setEditTriggers(self.table.EditTrigger.AllEditTriggers)
        self.table.itemChanged.connect(self.item_changed)
        lay.addWidget(self.table, 1)
        self.note = label('', 'subtitle')
        self.note.setWordWrap(True)
        lay.addWidget(self.note)
        bottom = QHBoxLayout()
        self.build_button = button(tr('Показать средний спектр'), lambda: self.average(), True)
        self.build_button.setEnabled(False)
        bottom.addWidget(self.build_button)
        bottom.addStretch(1)
        bottom.addWidget(button(tr('Закрыть'), self.reject))
        lay.addLayout(bottom)
        self.resize(720, 420)

    def choose(self):
        from modules.spectrum.views.reaction_view import RESULT_FILTER

        paths, _ = QFileDialog.getOpenFileNames(self, tr('Расчёты ЯМР конформеров'), '', tr(RESULT_FILTER))
        if paths:
            self.fill(self.paths + [p for p in paths if p not in self.paths])
        return paths

    def fill(self, paths):
        from modules.spectrum.analysis import ensemble

        outputs, texts = [], []
        try:
            for path in paths:
                output, text = self.read(path)
                if not output.shieldings:
                    raise ValueError(tr('В файле {} нет экранирований ЯМР.').format(Path(path).name))
                if _energy(output) is None:
                    raise ValueError(tr('В файле {} не нашлась энергия.').format(Path(path).name))
                outputs.append(output)
                texts.append(text)
            if len(outputs) > 1:
                ensemble.weighted_shieldings([o.shieldings for o in outputs], [1.0 / len(outputs)] * len(outputs))
        except (ValueError, OSError) as exc:
            self.note.setText(str(exc))
            return None
        self.paths, self.outputs, self.texts = [str(p) for p in paths], outputs, texts
        energies = [_energy(o) for o in outputs]
        low = min(energies)
        self.table.blockSignals(True)
        self.table.setRowCount(len(outputs))
        for r, (path, energy) in enumerate(zip(self.paths, energies)):
            values = (Path(path).name, f'{energy:.6f}', f'{(energy - low) * KJ:.2f}', '')
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if c != 2:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.table.setItem(r, c, item)
        self.table.blockSignals(False)
        self.note.setText('')
        self.update_shares()
        return [tuple(self.table.item(r, c).text() for c in range(4)) for r in range(len(outputs))]

    def item_changed(self, item):
        if item.column() == 2:
            self.update_shares()

    def shares(self):
        """The Boltzmann shares by the column ΔG (kJ/mol) at the temperature; None with the reason in the note."""
        from modules.spectrum.analysis import boltzmann

        values = []
        for r in range(self.table.rowCount()):
            text = self.table.item(r, 2).text().strip().replace(',', '.').replace('−', '-')
            try:
                values.append(float(text) / KJ)
            except ValueError:
                self.note.setText(tr('Строка {}: «{}» — не число.').format(r + 1, text))
                return None
        if len(values) < 2:
            return None
        try:
            return boltzmann.shares(values, self.temperature.value())
        except ValueError as exc:
            self.note.setText(str(exc))
            return None

    def update_shares(self):
        found = self.shares()
        self.table.blockSignals(True)
        for r in range(self.table.rowCount()):
            self.table.item(r, 3).setText('' if found is None else f'{100 * found[r]:.1f}')
        self.table.blockSignals(False)
        self.build_button.setEnabled(found is not None)
        if found is not None:
            self.note.setText('')
        return found

    def average(self):
        from modules.spectrum.analysis import ensemble

        found = self.shares()
        if found is None:
            return None
        made = (ensemble.weighted_shieldings([o.shieldings for o in self.outputs], found), list(self.outputs), found)
        self.built.emit(made)
        self.accept()
        return made
