"""The window «Донорно-акцепторная связь (CDA)» (the calculation: modules/spectrum/wavefunction/multiwfn_cda.py).

HEADER
    Opened by Compass after the queue «CDA» of Sextant and by «Связи» → «Донорно-акцепторная связь (CDA)…» of the
    result of its complex. Above — the sums in words: d (the donation from fragment 1 to fragment 2), b (the back
    donation), d − b, r (the repulsive polarization) and the net charge fragment 2 gets (ECDA); below — the table by
    complex orbital, the orbitals that carry most of the bond in bold; «Орбиталь на модели» puts the chosen one on the
    model of Compass.
§4 SPECIFICATION
    CdaDialog(parent, result (multiwfn_cda.parse_cda), formulas (fragment 1, fragment 2), written=[Path], orbital=None):
    .summary (QLabel), .table (QTableWidget), .orbital_button (with orbital — orbital(number) puts it on the model),
    .chosen() -> number | None; words(result, formulas) -> str (the summary).
§7 TESTS tests/test_gui.py::test_cda_queue_and_window.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QVBoxLayout

from azimuth.i18n import tr
from modules.spectrum.wavefunction import multiwfn_cda


def words(result, formulas):
    """The sums of CDA in a few sentences (what the numbers mean, after Dapprich and Frenking)."""
    s, one, two = result['sum'], formulas[0], formulas[1]
    text = tr(f'Донирование d ({one} → {two}) — <b>{s["d"]:.3f}</b> e, обратное донирование b ({two} → {one}) — '
              f'<b>{s["b"]:.3f}</b> e, d − b = {s["d_b"]:.3f} e; отталкивание r = {s["r"]:.3f} e')
    text += tr(' (< 0: электроны вытеснены из области между фрагментами).') if s['r'] < 0 else '.'
    if s['d'] > 0:
        ratio = s['b'] / s['d']
        text += ' ' + (tr(f'Обратное донирование — {ratio:.0%} от прямого: связь донорно-акцепторная с заметной '
                          'обратной π-составляющей.') if ratio >= 0.2 else
                       tr(f'Обратное донирование мало ({ratio:.0%} от прямого): связь — почти чистое донирование '
                          f'{one} → {two}.'))
    if result.get('net') is not None:
        text += ' ' + tr(f'Расширенный CDA (ECDA): фрагмент 2 в итоге получает {result["net"]:+.3f} e.')
    return text


class CdaDialog(QDialog):
    def __init__(self, parent, result, formulas, written=(), orbital=None):
        super().__init__(parent)
        self.result, self.formulas, self.orbital = result, tuple(formulas), orbital
        self.setWindowTitle(tr('Донорно-акцепторная связь (CDA)'))
        column = QVBoxLayout(self)
        column.setContentsMargins(18, 16, 18, 16)
        column.setSpacing(10)
        head = QLabel(tr(f'Анализ разложения заряда (CDA): фрагмент 1 — {self.formulas[0]}, фрагмент 2 — '
                         f'{self.formulas[1]}'))
        head.setObjectName('cardtitle')
        head.setWordWrap(True)
        column.addWidget(head)
        self.summary = QLabel(words(result, self.formulas))
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        column.addWidget(self.summary)
        header, rows = multiwfn_cda.table(result)
        self.table = QTableWidget(len(rows), len(header))
        self.table.setHorizontalHeaderLabels(header)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.setToolTip(tr('По занятым орбиталям комплекса: d — сколько электронов фрагмента 1 перешло на '
                                 'свободные орбитали фрагмента 2, b — обратно, r — смешивание занятых орбиталей обоих '
                                 '(отталкивание). Жирным — орбитали, на которых держится связь.'))
        main = {row[0] for row in multiwfn_cda.main_orbitals(result, 3)}
        for r, cells in enumerate(rows):
            for c, value in enumerate(cells):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if r < len(result['orbitals']) and result['orbitals'][r][0] in main or r == len(rows) - 1:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(r, c, item)
        column.addWidget(self.table, 1)
        note = QLabel(tr('Заселённости орбиталей — по Малликену (Multiwfn, обобщённый CDA). ')
                      + (tr('Таблица — в папке «Анализ» расчёта.') if written else ''))
        note.setObjectName('subtitle')
        note.setWordWrap(True)
        column.addWidget(note)
        last = QHBoxLayout()
        self.orbital_button = QPushButton(tr('Орбиталь на модели'))
        self.orbital_button.setToolTip(tr('Выбранная орбиталь комплекса — на модели Компаса'))
        self.orbital_button.clicked.connect(self.show_orbital)
        self.orbital_button.setVisible(orbital is not None)
        last.addWidget(self.orbital_button)
        last.addStretch(1)
        close = QPushButton(tr('Закрыть'))
        close.clicked.connect(self.accept)
        last.addWidget(close)
        column.addLayout(last)
        top = multiwfn_cda.main_orbitals(result, 1)
        if top:
            self.table.selectRow([row[0] for row in result['orbitals']].index(top[0][0]))
        self.resize(720, 560)

    def chosen(self):
        rows = self.table.selectionModel().selectedRows()
        if not rows or rows[0].row() >= len(self.result['orbitals']):
            return None
        return self.result['orbitals'][rows[0].row()][0]

    def show_orbital(self):
        number = self.chosen()
        if number is None or self.orbital is None:
            return False
        return bool(self.orbital(number))
