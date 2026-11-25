"""The window «Функции Фукуи» (the calculation: modules/spectrum/analysis/fukui.py).

HEADER
    Opened by Compass after the queue «Функции Фукуи (N, N+1, N−1)» of Sextant and by «±» → «Функции Фукуи…» of its
    result N. Above — the global indices (the ionization potential and the electron affinity, the electronegativity,
    the hardness, the electrophilicity index) and the most reactive atoms in words; below — the table by atom (the
    Hirshfeld charges of N, N + 1, N − 1, f⁺, f⁻, f⁰, Δf), the largest value of each column in bold. The values are on
    the model too — «±» chooses which (f⁺ is shown first).
§4 SPECIFICATION
    FukuiDialog(parent, symbols, charges {key: tuple}, values {'plus', 'minus', 'zero', 'dual'}, indices | None,
    written=[Path], surface=None); .summary (QLabel), .sites (QLabel), .table (QTableWidget), .leaders() -> {column:
    atom label};.surface_buttons {key: QPushButton} — surface(key) puts that field on the model.
§7 TESTS tests/test_gui.py::test_fukui_queue_and_window.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from azimuth.i18n import tr
from modules.spectrum.analysis.fukui import STATES

COLUMNS = (('plus', 'f⁺'), ('minus', 'f⁻'), ('zero', 'f⁰'), ('dual', 'Δf'))
SURFACE_TIPS = {'plus': 'f⁺ на модели: куда придёт электрон (атака нуклеофила)',
                'minus': 'f⁻ на модели: откуда уйдёт электрон (атака электрофила)',
                'zero': 'f⁰ на модели: атака радикала',
                'dual': 'Δf на модели: синее — электрофильные места, красное — нуклеофильные'}


class FukuiDialog(QDialog):
    def __init__(self, parent, symbols, charges, values, indices=None, written=(), surface=None):
        super().__init__(parent)
        self.surface = surface  # surface(key) puts the field f⁺, f⁻, f⁰ or Δf on the model of Compass
        self.symbols, self.charges, self.values, self.indices = list(symbols), charges, values, indices
        self.setWindowTitle(tr('Функции Фукуи'))
        column = QVBoxLayout(self)
        column.setContentsMargins(18, 16, 18, 16)
        column.setSpacing(10)
        head = QLabel(tr('Функции Фукуи и дескриптор двойственности'))
        head.setObjectName('cardtitle')
        column.addWidget(head)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextFormat(Qt.TextFormat.RichText)
        column.addWidget(self.summary)
        self.sites = QLabel()
        self.sites.setWordWrap(True)
        self.sites.setTextFormat(Qt.TextFormat.RichText)
        column.addWidget(self.sites)
        self.table = QTableWidget(len(self.symbols), 8)
        self.table.setHorizontalHeaderLabels([tr('Атом'), 'q(N)', 'q(N+1)', 'q(N−1)', 'f⁺', 'f⁻', 'f⁰', 'Δf'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setToolTip(tr('Заряды Хиршфельда трёх расчётов. f⁺ = q(N) − q(N+1): куда придёт электрон — атака '
                                 'нуклеофила; f⁻ = q(N−1) − q(N): откуда уйдёт электрон — атака электрофила; f⁰ — '
                                 'их среднее, атака радикала; Δf = f⁺ − f⁻: > 0 — электрофильный центр, < 0 — '
                                 'нуклеофильный'))
        column.addWidget(self.table, 1)
        note = QLabel(tr('На модели — f⁺; другие столбцы выбираются в «Атомы» Компаса.')
                      + (' ' + tr('Таблица — в папке «Анализ» расчёта.') if written else ''))
        note.setObjectName('subtitle')
        note.setWordWrap(True)
        column.addWidget(note)
        close = QPushButton(tr('Закрыть'))
        close.clicked.connect(self.accept)
        last = QHBoxLayout()
        # the fields themselves — a ± surface on the model (the densities of the three calculations)
        self.surface_buttons = {}
        if surface is not None:
            caption = QLabel(tr('Поверхность на модели:'))
            caption.setObjectName('subtitle')
            last.addWidget(caption)
            for key, name in COLUMNS:
                item = QPushButton(name)
                item.setToolTip(tr(SURFACE_TIPS[key]))
                item.clicked.connect(lambda checked=False, k=key: self.surface(k))
                self.surface_buttons[key] = item
                last.addWidget(item)
        last.addStretch(1)
        last.addWidget(close)
        column.addLayout(last)
        self.fill()
        self.resize(720, 560)

    def label(self, k):
        return f'{self.symbols[k]}{k + 1}'

    def leaders(self):
        """The atom of the largest f⁺, f⁻, f⁰, Δf and of the smallest Δf."""
        found = {}
        for key, _ in COLUMNS:
            row = self.values[key]
            found[key] = self.label(max(range(len(row)), key=row.__getitem__))
        dual = self.values['dual']
        found['dual-min'] = self.label(min(range(len(dual)), key=dual.__getitem__))
        return found

    def fill(self):
        g = self.indices
        if g:
            omega = f'{g["omega"]:.2f}' if g.get('omega') is not None else '—'
            self.summary.setText(tr(f'Потенциал ионизации <b>{g["ip"]:.2f}</b> эВ, сродство к электрону '
                                    f'<b>{g["ea"]:.2f}</b> эВ (вертикальные); электроотрицательность χ {g["chi"]:.2f} эВ, '
                                    f'жёсткость η {g["eta"]:.2f} эВ, индекс электрофильности ω {omega} эВ.'))
        else:
            self.summary.setText(tr('Глобальные индексы не посчитаны: нет энергий трёх расчётов.'))
        lead = self.leaders()
        self.sites.setText(tr(f'Атака нуклеофила — скорее всего на <b>{lead["plus"]}</b> (наибольшая f⁺), электрофила — '
                              f'на <b>{lead["minus"]}</b> (f⁻), радикала — на <b>{lead["zero"]}</b> (f⁰). Самый '
                              f'электрофильный центр по Δf — {lead["dual"]}, самый нуклеофильный — {lead["dual-min"]}.'))
        tops = {c: max(range(len(self.symbols)), key=self.values[key].__getitem__) for c, (key, _) in enumerate(COLUMNS, 4)}
        for k in range(len(self.symbols)):
            cells = [self.label(k)] + [f'{self.charges[key][k]:+.4f}' for key in STATES] + [
                f'{self.values[key][k]:+.4f}' if key == 'dual' else f'{self.values[key][k]:.4f}' for key, _ in COLUMNS]
            for c, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if tops.get(c) == k:
                    font = item.font()
                    font.setBold(True)
                    item.setFont(font)
                self.table.setItem(k, c, item)
