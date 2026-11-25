"""Compact element picker; all elements remain available independently of export support."""

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QDialog, QVBoxLayout, QGridLayout, QLabel, QPushButton
from azimuth.core import SYMBOLS
from azimuth.i18n import tr

ROWS = [
    ['H'] + [''] * 16 + ['He'],
    ['Li', 'Be'] + [''] * 10 + ['B', 'C', 'N', 'O', 'F', 'Ne'],
    ['Na', 'Mg'] + [''] * 10 + ['Al', 'Si', 'P', 'S', 'Cl', 'Ar'],
    'K Ca Sc Ti V Cr Mn Fe Co Ni Cu Zn Ga Ge As Se Br Kr'.split(),
    'Rb Sr Y Zr Nb Mo Tc Ru Rh Pd Ag Cd In Sn Sb Te I Xe'.split(),
    'Cs Ba * Hf Ta W Re Os Ir Pt Au Hg Tl Pb Bi Po At Rn'.split(),
    'Fr Ra ** Rf Db Sg Bh Hs Mt Ds Rg Cn Nh Fl Mc Lv Ts Og'.split(),
    ['', ''] + 'La Ce Pr Nd Pm Sm Eu Gd Tb Dy Ho Er Tm Yb Lu'.split(),
    ['', ''] + 'Ac Th Pa U Np Pu Am Cm Bk Cf Es Fm Md No Lr'.split(),
]


# the element chosen in the blue of the program (QPushButton:checked of azimuth/app.STYLE), not teal


class PeriodicTable(QDialog):
    selected = Signal(str)
    isotope = Signal(str, float)  # an element chosen with its isotope (the menu of the right button)

    def __init__(self, current, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Выберите элемент'))
        self.setModal(False)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr('Таблица Менделеева · выберите атом для добавления')))
        grid = QGridLayout()
        grid.setSpacing(3)
        layout.addLayout(grid)
        self.buttons = {}
        for row, entries in enumerate(ROWS):
            for col, symbol in enumerate(entries):
                if not symbol:
                    continue
                if symbol in ('*', '**'):
                    grid.addWidget(QLabel('57–71' if symbol == '*' else '89–103'), row, col)
                    continue
                b = QPushButton(f'{SYMBOLS.index(symbol) + 1}\n{symbol}')
                b.setFixedSize(40, 43)
                b.setCheckable(True)
                b.setChecked(symbol == current)
                b.setAccessibleName(tr(f'{symbol}, атомный номер {SYMBOLS.index(symbol) + 1}'))
                b.setStyleSheet('QPushButton {padding: 0;} QPushButton:checked {background: #2a62b8; color: white; border-color: #2a62b8;}')
                b.clicked.connect(lambda checked=False, s=symbol: self.choose(s))
                # the right button — its isotopes
                b.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
                b.customContextMenuRequested.connect(lambda point, s=symbol, w=b: self.isotope_menu(s, w, point))
                b.setToolTip(tr('Правая кнопка — изотопы'))
                grid.addWidget(b, row, col)
                self.buttons[symbol] = b
        # the dummy atom X (as in Chemcraft) — a point without a nucleus, under the lanthanides
        dummy = QPushButton('·\nX')
        dummy.setFixedSize(40, 43)
        dummy.setCheckable(True)
        dummy.setChecked(current == 'X')
        dummy.setToolTip(tr('Атом-призрак X: точка без ядра и электронов — для Z-матрицы, центра цикла, оси. В расчёт не входит.'))
        dummy.setAccessibleName(tr('Атом-призрак X'))
        dummy.setStyleSheet('QPushButton {padding: 0; border-style: dashed;} QPushButton:checked {background: #2a62b8; color: white; border-color: #2a62b8;}')
        dummy.clicked.connect(lambda checked=False: self.choose('X'))
        grid.addWidget(dummy, len(ROWS) - 1, 0)
        self.buttons['X'] = dummy
        note = QLabel(tr('Все 118 элементов доступны для построения. Поддержка экспорта зависит от метода и базиса.'))
        note.setWordWrap(True)
        layout.addWidget(note)

    def choose(self, symbol):
        self.selected.emit(symbol)
        self.accept()

    def isotope_menu(self, symbol, button, point):
        """The isotopes of the element (azimuth.core.ISOTOPES with their abundance) and «Своя масса…»; a choice is the
        element with that isotope (signals selected, then isotope). -> the menu."""
        from PySide6.QtWidgets import QInputDialog, QMenu

        from azimuth.core import ISOTOPES, isotope_abundance
        from azimuth.isotope_table import STABLE
        from azimuth.ui import rounded

        menu = rounded(QMenu(self))
        head = menu.addAction(tr('Изотоп {}').format(symbol))
        head.setEnabled(False)

        def pick(mass):
            self.selected.emit(symbol)
            self.isotope.emit(symbol, float(mass))
            self.accept()

        for name, mass in ISOTOPES.get(symbol, []):
            share = isotope_abundance(symbol, mass)
            text = f'{name} · {mass:.4f}' + (f'  ({share * 100:.3g} %)' if share is not None
                                             else '  (' + tr('радиоактивный') + ')')
            menu.addAction(text).triggered.connect(lambda checked=False, m=mass: pick(m))
        menu.addSeparator()

        def own():
            start = max(STABLE.get(symbol, ((0, 1.0, 1.0),)), key=lambda item: item[2])[1]
            value, ok = QInputDialog.getDouble(self, tr('Своя масса'), tr('Масса атома {}, а. е. м.:').format(symbol),
                                               float(start), 0.5, 400.0, 6)
            if ok:
                pick(value)

        menu.addAction(tr('Своя масса…')).triggered.connect(lambda checked=False: own())
        self._isotope_menu = menu
        menu.popup(button.mapToGlobal(point))
        return menu
