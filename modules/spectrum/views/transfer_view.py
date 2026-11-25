"""Spectrum: the window «Перенос заряда» of an excited state — IFCT between fragments and the transition matrix as a
heat map (the calculation: modules/spectrum/analysis/charge_transfer.py).

HEADER From «UV-Vis» («Перенос заряда…» next to «Анализ возбуждений», for the state chosen in the table). The fragments
    are typed as numbers of atoms («1,2,9» — one fragment per field; one fragment — the rest of the molecule is the
    second), or taken from the atoms selected in Compass. «Посчитать»: the summary (charge transfer or a local
    excitation — CT and LE, intrinsic and apparent), the table of the fragments (their shares of the hole and the
    electron, the change of their population, the redistribution inside), the electrons moved between every pair, and
    the heat map of the transition matrix — by fragments or by atoms (with the hydrogens). The tables go to «Анализ»
    next to the file of the orbitals («<name>_charge_transfer_S<k>.csv»).
§4 SPECIFICATION
    HeatMap(): set_matrix(matrix, labels); .matrix, .labels.
    ChargeTransferDialog(parent, given, state, label, symbols, selection=None): given = (program, wavefunction, output,
    cores); .fragment_edits, .compute() -> bool, .result (parse_ifct), .atoms_matrix, .fragment_matrix, .heat, .view.
§7 TESTS tests/test_gui.py::test_charge_transfer_window.
"""

from pathlib import Path

import numpy as np
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from azimuth.i18n import tr


class HeatMap(QWidget):
    """A square matrix as colored cells: the base color of the theme for 0, the accent for the largest value; the labels
    of the rows and the columns; the value of a cell in its tooltip."""

    def __init__(self):
        super().__init__()
        self.matrix, self.labels = None, []
        self.setMinimumSize(260, 260)
        self.setMouseTracking(True)

    def set_matrix(self, matrix, labels):
        self.matrix = None if matrix is None else np.asarray(matrix, dtype=float)
        self.labels = list(labels)
        self.update()

    def _geometry(self):
        n = len(self.matrix)
        side = max(1.0, min(self.width() - 56, self.height() - 40) / n)
        return n, side, 48.0, 8.0

    def paintEvent(self, event):
        if self.matrix is None or not len(self.matrix):
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        n, side, left, top = self._geometry()
        palette = self.palette()
        base, accent, text = palette.base().color(), QColor('#2a62b8'), palette.text().color()
        if base.lightness() < 128:
            accent = QColor('#6ea2f0')
        top_value = float(self.matrix.max()) or 1.0
        for i in range(n):
            for j in range(n):
                t = max(0.0, min(1.0, self.matrix[i, j] / top_value)) ** 0.5  # the small ones visible too
                color = QColor(round(base.red() + (accent.red() - base.red()) * t),
                               round(base.green() + (accent.green() - base.green()) * t),
                               round(base.blue() + (accent.blue() - base.blue()) * t))
                painter.fillRect(QRectF(left + j * side, top + i * side, side, side), color)
        painter.setPen(text)
        font = painter.font()
        font.setPointSizeF(max(7.0, min(11.0, side * 0.45)))
        painter.setFont(font)
        for k, name in enumerate(self.labels[:n]):
            painter.drawText(QRectF(0, top + k * side, left - 4, side), Qt.AlignmentFlag.AlignRight
                             | Qt.AlignmentFlag.AlignVCenter, name)
            painter.drawText(QRectF(left + k * side, top + n * side + 2, side, 24), Qt.AlignmentFlag.AlignHCenter
                             | Qt.AlignmentFlag.AlignTop, name)
        painter.end()

    def mouseMoveEvent(self, event):
        if self.matrix is None or not len(self.matrix):
            return
        n, side, left, top = self._geometry()
        j, i = int((event.position().x() - left) // side), int((event.position().y() - top) // side)
        if 0 <= i < n and 0 <= j < n:
            names = self.labels + [''] * n
            self.setToolTip(f'{names[i]} · {names[j]}: {self.matrix[i, j]:.4f}')
        else:
            self.setToolTip('')


class ChargeTransferDialog(QDialog):
    def __init__(self, parent, given, state, label, symbols, selection=None):
        super().__init__(parent)
        self.given, self.state, self.symbols = given, int(state), list(symbols)
        self.result = self.atoms_matrix = self.fragment_matrix = None
        self.parts = []
        self.setWindowTitle(tr(f'Перенос заряда · {label}'))
        column = QVBoxLayout(self)
        column.setContentsMargins(18, 16, 18, 16)
        column.setSpacing(10)
        head = QLabel(tr(f'Перенос заряда · {label}'))
        head.setObjectName('cardtitle')
        column.addWidget(head)
        note = QLabel(tr('Фрагменты — атомы номерами или с символом («1,2,9», «3-8», «O1, C2, H9», «C3–C8»). Один '
                         'фрагмент — остальная молекула станет вторым. Дырка — откуда уходит электрон, электрон — куда '
                         'приходит.'))
        note.setObjectName('subtitle')
        note.setWordWrap(True)
        column.addWidget(note)
        self.fragment_edits = []
        row = QHBoxLayout()
        for k in range(3):
            edit = QLineEdit()
            edit.setPlaceholderText(tr(f'Фрагмент {k + 1}') + ('' if k == 0 else tr(' (необязательно)')))
            self.fragment_edits.append(edit)
            row.addWidget(edit, 1)
        self.selection_button = QPushButton(tr('Из выделения в Компасе'))
        self.selection_button.setToolTip(tr('Атомы, выделенные на модели Компаса, — первым фрагментом'))
        self.selection = selection
        self.selection_button.setEnabled(selection is not None)
        self.selection_button.clicked.connect(self.take_selection)
        row.addWidget(self.selection_button)
        self.compute_button = QPushButton(tr('Посчитать'))
        self.compute_button.setObjectName('primary')
        self.compute_button.clicked.connect(self.compute)
        row.addWidget(self.compute_button)
        column.addLayout(row)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        column.addWidget(self.summary)
        body = QHBoxLayout()
        tables = QVBoxLayout()
        self.table = QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([tr('Фрагмент'), tr('Атомы'), tr('Дырка, %'), tr('Электрон, %'), tr('Δn, e'),
                                              tr('Внутри, e')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setToolTip(tr('Δn — изменение числа электронов фрагмента при возбуждении; «Внутри» — электроны, '
                                 'перераспределённые внутри фрагмента (локальная часть)'))
        tables.addWidget(self.table, 1)
        self.transfers = QLabel()
        self.transfers.setWordWrap(True)
        self.transfers.setObjectName('subtitle')
        tables.addWidget(self.transfers)
        body.addLayout(tables, 3)
        maps = QVBoxLayout()
        self.view = QComboBox()
        self.view.addItem(tr('Матрица перехода по фрагментам'), 'fragments')
        self.view.addItem(tr('Матрица перехода по атомам'), 'atoms')
        self.view.setToolTip(tr('Сумма квадратов элементов матрицы плотности перехода между атомами (фрагментами): '
                                'где лежат дырка и электрон и как они связаны'))
        self.view.currentIndexChanged.connect(lambda *a: self.show_map())
        maps.addWidget(self.view)
        self.heat = HeatMap()
        maps.addWidget(self.heat, 1)
        body.addLayout(maps, 2)
        column.addLayout(body, 1)
        from azimuth.ui import StatusEcho

        self.status = StatusEcho()  # «Таблица в „Анализ“…» — in the status line, not a line here
        self.status.setObjectName('subtitle')
        column.addWidget(self.status)
        close = QPushButton(tr('Закрыть'))
        close.clicked.connect(self.accept)
        last = QHBoxLayout()
        last.addStretch(1)
        last.addWidget(close)
        column.addLayout(last)
        self.resize(900, 560)

    def take_selection(self):

        atoms = self.selection() if self.selection is not None else []
        if atoms:
            from azimuth import atom_labels

            self.fragment_edits[0].setText(atom_labels.text([a + 1 for a in atoms], self.symbols))  # «H1»
            for edit in self.fragment_edits[1:]:
                edit.clear()
        else:
            self.status.setText(tr('В Компасе ничего не выделено.'))

    def names(self, parts):
        return [tr(f'Ф{k + 1}') for k in range(len(parts))]

    def compute(self):
        from azimuth.tasks import run_waiting
        from modules.spectrum.analysis import charge_transfer as ct

        try:
            parts = ct.fragments([e.text() for e in self.fragment_edits], len(self.symbols), self.symbols)
        except ValueError as exc:
            self.status.setText(str(exc))
            return False
        program, path, output, cores = self.given

        def work(step):
            result, text = ct.run_ifct(program, path, output, self.state, parts, cores, step)
            fragment, _ = ct.run_matrix(program, path, output, self.state, parts, cores, step)
            atoms, _ = ct.run_matrix(program, path, output, self.state, None, cores, step)
            return result, text, fragment, atoms

        try:
            found = run_waiting(self, tr('Перенос заряда…'), work)
        except InterruptedError:
            return False
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc))
            return False
        self.result, text, self.fragment_matrix, self.atoms_matrix = found
        self.parts = parts
        self.fill()
        self.save(text)
        return True

    def fill(self):
        from azimuth import atom_labels

        r, parts = self.result, self.parts
        kind = tr('перенос заряда') if r.get('ct', 0) >= 50 else tr('в основном локальное возбуждение')
        self.summary.setText(tr(f'<b>{kind}</b>: перенос заряда (собственный) {r.get("ct", 0):.1f} %, локальное '
                                f'{r.get("le", 0):.1f} %; видимый перенос {r.get("ct_apparent", 0):.1f} %'))
        self.table.setRowCount(len(parts))
        names = self.names(parts)
        for k, atoms in enumerate(parts):
            cells = [names[k], atom_labels.text(atoms, self.symbols), r['hole'][k], r['electron'][k],
                     r['variation'][k] if k < len(r['variation']) else '',
                     r['redistribution'][k] if k < len(r['redistribution']) else '']
            for c, value in enumerate(cells):
                text = value if isinstance(value, str) else (f'{value:.2f}' if c in (2, 3) else f'{value:+.3f}' if c == 4
                                                             else f'{value:.3f}')
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.table.setItem(k, c, item)
        lines = []
        for (i, j), moved in sorted(r['transfer'].items()):
            if i < j:
                back = r['transfer'].get((j, i), 0.0)
                net = r['net'].get((i, j), moved - back)
                lines.append(tr(f'{names[i - 1]} → {names[j - 1]}: {moved:.3f} e, обратно {back:.3f} e, итог '
                                f'{names[i - 1] if net >= 0 else names[j - 1]} → {names[j - 1] if net >= 0 else names[i - 1]}'
                                f' {abs(net):.3f} e'))
        self.transfers.setText('\n'.join(lines))
        self.show_map()

    def show_map(self):
        if self.view.currentData() == 'atoms' and self.atoms_matrix is not None:
            labels = [f'{s}{k + 1}' for k, s in enumerate(self.symbols)]
            self.heat.set_matrix(self.atoms_matrix, labels)
        elif self.fragment_matrix is not None:
            self.heat.set_matrix(self.fragment_matrix, self.names(self.parts))

    def save(self, text):
        from azimuth import atom_labels
        from modules.spectrum.wavefunction import field_tables

        program, path, output, cores = self.given
        r, names = self.result, self.names(self.parts)
        header = [tr('Фрагмент'), tr('Атомы'), tr('Дырка, %'), tr('Электрон, %'), tr('Δn, e'), tr('Внутри, e')]
        rows = [[names[k], atom_labels.text(a, self.symbols), f'{r["hole"][k]:.2f}', f'{r["electron"][k]:.2f}',
                 f'{r["variation"][k]:+.5f}' if k < len(r['variation']) else '',
                 f'{r["redistribution"][k]:.5f}' if k < len(r['redistribution']) else '']
                for k, a in enumerate(self.parts)]
        rows.append([tr('CT, % (собств. / видимый)'), '', f'{r.get("ct", 0):.3f}', f'{r.get("ct_apparent", 0):.3f}', '', ''])
        base = Path(path)
        try:
            field_tables.write_tables(base.parent, base.name.split('.')[0],
                                      {f'charge_transfer_S{self.state}': (header, rows)})
            field_tables.save_output(path, f'ifct_S{self.state}', text)
            self.status.setText(tr('Таблица — в папке «Анализ» расчёта.'))
        except OSError as exc:
            self.status.setText(tr('Таблица не записана: ') + str(exc))
