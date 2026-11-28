"""«Опыт» of Spectrum: the result of a molecule next to its measured values (analysis/measured.py, analysis/cccbdb.py).

MeasuredPanel.load(output, level='') -> bool — True (the tab shown) for a molecule of up to measured.LARGEST atoms.
The 30 molecules of the course are known without the network; another molecule found before is read from the folder
of the user (cccbdb.cached); else «Найти в CCCBDB» looks for it on the network (PubChem → CAS → the page of CCCBDB,
cccbdb.find) in a worker thread, the answer by a queued signal (as «Найти в NIST…»); search_function is replaced in
the tests (no network there). Two cards side by side: the frequencies (the computed ones paired in order with the
measured fundamentals, the differences, the factor that brings them together and the factor of CCCBDB for the level of
the result; against the harmonic frequencies of experiment too where CCCBDB has them) and the structure and the
properties (the bonds, the dipole moment; the ionization energy and the enthalpy of formation as measured). The
source of the values and the page of the molecule in CCCBDB under them.
§7 TESTS tests/spectrum/test_measured.py, tests/spectrum/test_cccbdb.py (the numbers), tests/gui/test_gui_spectrum.py
(the tab, the search).
"""

import threading

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import card


def _table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels(headers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
    table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.verticalHeader().hide()
    return table


def _fill(table, rows):
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            item = QTableWidgetItem(value)
            if c:
                item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            table.setItem(r, c, item)


def _signed(value, digits):
    return '—' if value is None else f'{value:+.{digits}f}'


class _Relay(QObject):
    done = Signal(object)


class MeasuredPanel(QWidget):
    def __init__(self):
        super().__init__()
        from modules.spectrum.analysis import cccbdb

        self.comparison, self.output, self.level, self.busy = None, None, '', False
        self.search_function = cccbdb.find
        self.cached_function = cccbdb.cached
        self.relay = _Relay(self)
        self.relay.done.connect(self.answer)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 8, 0, 0)
        head = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName('cardtitle')
        self.title.setWordWrap(True)
        head.addWidget(self.title, 1)
        self.search_button = QPushButton(tr('Найти в CCCBDB'))
        self.search_button.setToolTip(tr('Опытные данные молекулы из NIST CCCBDB: номер CAS — по SMILES из PubChem, затем '
                                         'страница молекулы. Нужен интернет; отправляется только SMILES.'))
        self.search_button.clicked.connect(self.search)
        head.addWidget(self.search_button)
        column.addLayout(head)
        self.state = QLabel()
        self.state.setObjectName('subtitle')
        self.state.setWordWrap(True)
        column.addWidget(self.state)
        self.cards = QWidget()
        cards = QHBoxLayout(self.cards)
        cards.setContentsMargins(0, 0, 0, 0)
        cards.setSpacing(12)
        modes_card, modes_box = card(tr('Частоты · см⁻¹'))
        modes_box.setContentsMargins(14, 12, 14, 14)
        self.modes = _table([tr('Симметрия'), tr('Расчёт'), tr('Опыт'), tr('Δ')])
        modes_box.addWidget(self.modes, 1)
        self.modes_note = QLabel()
        self.modes_note.setObjectName('subtitle')
        self.modes_note.setWordWrap(True)
        modes_box.addWidget(self.modes_note)
        cards.addWidget(modes_card, 1)
        props_card, props_box = card(tr('Строение и свойства'))
        props_box.setContentsMargins(14, 12, 14, 14)
        self.properties = _table([tr('Величина'), tr('Расчёт'), tr('Опыт'), tr('Δ')])
        props_box.addWidget(self.properties, 1)
        cards.addWidget(props_card, 1)
        column.addWidget(self.cards, 1)
        self.source = QLabel()
        self.source.setObjectName('subtitle')
        self.source.setWordWrap(True)
        self.source.setOpenExternalLinks(True)
        self.source.setTextFormat(Qt.TextFormat.RichText)
        column.addWidget(self.source)

    @staticmethod
    def _geometry(output):
        return getattr(output, 'geometry', None) or getattr(output, 'vibration_geometry', None)

    def load(self, output, level=''):
        from modules.spectrum.analysis import measured

        self.output, self.level, self.comparison = output, level, None
        geometry = self._geometry(output) if output is not None else None
        if not measured.searchable(geometry):
            return False
        entry = measured.identify(geometry)
        if entry is None:
            try:
                entry = self.cached_function(geometry)
            except Exception:  # noqa: BLE001 — a kept file of another version: searched anew
                entry = None
        if entry is not None:
            self.show_entry(entry)
            return True
        self.title.setText(tr('{} — опыт из CCCBDB').format(geometry.formula))
        self.state.setText(tr('Этой молекулы нет среди 30 молекул курса. «Найти в CCCBDB» поищет её опытные данные '
                              'в сети (около двух тысяч молекул).'))
        self.state.show()
        self.search_button.setVisible(True)
        self.search_button.setEnabled(not self.busy)
        self.cards.hide()
        self.source.clear()
        return True

    def search(self):
        geometry = self._geometry(self.output)
        if self.busy or geometry is None:
            return False
        self.busy = True
        self.search_button.setEnabled(False)
        self.state.setText(tr('Ищу в PubChem и CCCBDB…'))
        asked = self.output

        def work():
            try:
                found = ('entry', self.search_function(geometry))
            except ValueError as exc:
                found = ('error', str(exc))
            except Exception as exc:  # noqa: BLE001 — never an exception in the window
                found = ('error', f'{type(exc).__name__}: {exc}')
            try:
                self.relay.done.emit((asked, found))
            except RuntimeError:  # the window was closed meanwhile
                pass

        threading.Thread(target=work, name='azimuth-cccbdb', daemon=True).start()
        return True

    def answer(self, message):
        asked, (kind, value) = message
        self.busy = False
        self.search_button.setEnabled(True)
        if asked is not self.output:  # another result was opened meanwhile
            return
        if kind == 'error':
            self.state.setText(value)
        elif value is None:
            self.state.setText(tr('В CCCBDB опытных данных этой молекулы нет (или PubChem не знает её номер CAS).'))
        else:
            self.show_entry(value)

    def show_entry(self, entry):
        from modules.spectrum.analysis import measured

        self.comparison = found = measured.compare(entry, self.output)
        self.search_button.setVisible(False)
        self.state.hide()
        self.cards.show()
        formula = entry.get('formula') or ''
        self.title.setText(tr('{} ({}) — расчёт и опыт').format(measured.name(entry).capitalize(), formula))
        vib = found.vibrations
        if vib is not None and vib.pairs:
            _fill(self.modes, [(label, f'{w:.0f}', f'{nu:.0f}', f'{w - nu:+.0f}') for w, nu, label in vib.pairs])
            lines = [tr('Средняя разница {:.0f} см⁻¹: гармонические частоты выше наблюдаемых.').format(vib.mean_abs),
                     tr('Множитель для этой молекулы {:.3f} (после него — {:.0f} см⁻¹).').format(vib.factor,
                                                                                         vib.mean_abs_scaled)]
            from modules.spectrum.analysis import scaling

            known = scaling.recommended(self.level) if self.level else None
            if known is not None:
                lines.append(tr('Множитель CCCBDB для {}/{}: {:.3f}.').format(known.method, known.basis, known.factor)
                             + ('' if known.exact else ' ' + tr('(такого базиса в CCCBDB нет — взят базис того же '
                                                                'размера)')))
            if found.harmonic is not None:
                lines.append(tr('С гармоническими частотами опыта средняя разница {:.0f} см⁻¹ — это ошибка самого метода, '
                                'без ангармоничности.').format(found.harmonic.mean_abs))
            lines.append(tr('Пары составлены по порядку частот, без симметрии: две близкие моды могут поменяться.'))
            self.modes_note.setText(' '.join(lines))
        else:
            _fill(self.modes, [])
            self.modes_note.setText(vib.reason if vib is not None else tr('В результате нет частот.'))
        rows = []
        for row in found.bonds:
            rows.append((tr('Длина {}, Å').format(row.pair), '—' if row.computed is None else f'{row.computed:.3f}',
                         f'{row.measured:.3f}', _signed(row.delta, 3)))
        if found.dipole is not None:
            computed, measured_value = found.dipole
            rows.append((tr('Дипольный момент, Д'), '—' if computed is None else f'{computed:.2f}',
                         f'{measured_value:.2f}', '—' if computed is None else f'{computed - measured_value:+.2f}'))
        if entry.get('ie_ev') is not None:
            rows.append((tr('Энергия ионизации, эВ'), '—', f"{entry['ie_ev']:.2f}", '—'))
        if entry.get('hf298_kj') is not None:
            rows.append((tr('ΔfH°(298 К), газ, кДж/моль'), '—', f"{entry['hf298_kj']:.1f}", '—'))
        _fill(self.properties, rows)
        if found.hints:  # far from experiment: another conformer, most likely
            self.state.setText('⚠ ' + ' '.join(found.hints))
            self.state.show()
        notes = ' '.join(tr(n) for n in found.notes)
        self.source.setText(
            (notes + ' ' if notes else '')
            + tr('Опыт: {} — <a href="{}">страница молекулы</a>; ΔfH — {}.').format(measured.SOURCE, measured.url(entry),
                                                                              entry.get('hf_source') or 'CCCBDB')
            + (' ' + tr('Найдено в сети и сохранено на этом компьютере.') if entry.get('online') else '')
            + ' ' + tr('Энергия ионизации и ΔfH даны для расчётов, которые их считают (ΔSCF, термохимический '
                       'рецепт); полная энергия одной молекулы с ними не сравнивается.'))
        return True
