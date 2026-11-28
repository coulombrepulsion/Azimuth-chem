"""«Опыт» of Spectrum: the result of a molecule of the course next to its measured values (analysis/measured.py).

MeasuredPanel.load(output, level='') -> bool — the tab is shown only when the molecule of the result is one of the
file (True). Two cards side by side: the frequencies (the computed ones paired in order with the measured
fundamentals, the differences, the factor that brings them together and the factor of CCCBDB for the level of the
result) and the structure and the properties (the bonds, the dipole moment; the ionization energy and the enthalpy of
formation as measured). The source of the values and the page of the molecule in CCCBDB under them.
§7 TESTS tests/spectrum/test_measured.py (the numbers), tests/gui/test_gui_spectrum.py (the tab).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget

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


class MeasuredPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.comparison = None
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 8, 0, 0)
        self.title = QLabel()
        self.title.setObjectName('cardtitle')
        self.title.setWordWrap(True)
        column.addWidget(self.title)
        cards = QHBoxLayout()
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
        column.addLayout(cards, 1)
        self.source = QLabel()
        self.source.setObjectName('subtitle')
        self.source.setWordWrap(True)
        self.source.setOpenExternalLinks(True)
        self.source.setTextFormat(Qt.TextFormat.RichText)
        column.addWidget(self.source)

    def load(self, output, level=''):
        from modules.spectrum.analysis import measured

        geometry = getattr(output, 'geometry', None) or getattr(output, 'vibration_geometry', None)
        entry = measured.identify(geometry) if output is not None else None
        self.comparison = measured.compare(entry, output) if entry is not None else None
        if self.comparison is None:
            return False
        found = self.comparison
        self.title.setText(tr('{} ({}) — расчёт и опыт').format(measured.name(entry).capitalize(), entry['formula']))
        vib = found.vibrations
        if vib is not None and vib.pairs:
            _fill(self.modes, [(label, f'{w:.0f}', f'{nu:.0f}', f'{w - nu:+.0f}') for w, nu, label in vib.pairs])
            lines = [tr('Средняя разница {:.0f} см⁻¹: гармонические частоты выше наблюдаемых.').format(vib.mean_abs),
                     tr('Множитель для этой молекулы {:.3f} (после него — {:.0f} см⁻¹).').format(vib.factor,
                                                                                         vib.mean_abs_scaled)]
            from modules.spectrum.analysis import scaling

            known = scaling.recommended(level) if level else None
            if known is not None:
                lines.append(tr('Множитель CCCBDB для {}/{}: {:.3f}.').format(known.method, known.basis, known.factor)
                             + ('' if known.exact else ' ' + tr('(такого базиса в CCCBDB нет — взят базис того же '
                                                                'размера)')))
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
        notes = ' '.join(tr(n) for n in found.notes)
        self.source.setText(
            (notes + ' ' if notes else '')
            + tr('Опыт: {} — <a href="{}">страница молекулы</a>; ΔfH — {}.').format(measured.SOURCE, measured.url(entry),
                                                                              entry.get('hf_source') or 'CCCBDB')
            + ' ' + tr('Энергия ионизации и ΔfH даны для расчётов, которые их считают (ΔSCF, термохимический '
                       'рецепт); полная энергия одной молекулы с ними не сравнивается.'))
        return True
