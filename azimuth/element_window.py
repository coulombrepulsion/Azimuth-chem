"""«Справка → Таблица Менделеева»: the periodic table and the isotopes; a click on an element shows a
small animation of its atom — the nucleus of protons and neutrons, the electrons going round it by shells — its mass,
how many protons, neutrons and electrons, its electron configuration and its isotopes (azimuth/elements.py,
azimuth/isotope_table.py)."""

from math import cos, pi, sin, sqrt

from PySide6.QtCore import QPointF, Qt, QTimer
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QDialog, QGridLayout, QGroupBox, QHBoxLayout, QHeaderView, QLabel,
                               QLayout, QPushButton, QTableWidget, QTableWidgetItem, QWidget)

from azimuth import elements
from azimuth.core import SYMBOLS
from azimuth.i18n import tr
from azimuth.isotope_table import STABLE, SUPERSCRIPT

SHELLS = 'KLMNOPQ'
PROTON, NEUTRON, ELECTRON = '#d65454', '#8a9bb0', '#2a62b8'
GOLDEN = pi * (3 - sqrt(5))


class AtomView(QWidget):
    """The atom drawn: the nucleus (protons red, neutrons grey, packed as a disc), the shells K, L … as circles with
    their electrons going round — the outer ones slower. set_atom(z, a)."""

    FRAME_MS = 33

    def __init__(self, parent=None):
        super().__init__(parent)
        self.z, self.a, self.t = 1, 1, 0.0
        self.setMinimumSize(280, 280)
        self.timer = QTimer(self)
        self.timer.setInterval(self.FRAME_MS)
        self.timer.timeout.connect(self._step)

    def set_atom(self, z, a):
        self.z, self.a = int(z), max(int(a), int(z))
        self.update()

    def _step(self):
        self.t += self.FRAME_MS / 1000
        self.update()

    def showEvent(self, event):
        self.timer.start()
        super().showEvent(event)

    def hideEvent(self, event):
        self.timer.stop()
        super().hideEvent(event)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self.palette().window().color().lightnessF() < 0.5
        ink = QColor('#e7eaf0' if dark else '#1b2230')
        centre = QPointF(self.width() / 2, self.height() / 2)
        room = min(self.width(), self.height()) / 2 - 16
        counts = elements.shells(self.z)
        nucleus = min(room * 0.28, 7 + 2.4 * self.a ** (1 / 3))
        # the shells
        step = (room - nucleus - 10) / max(1, len(counts))
        faint = QColor(ink)
        faint.setAlpha(60)
        for k, count in enumerate(counts):
            radius = nucleus + 10 + step * (k + 0.8)
            p.setPen(QPen(faint, 1))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(centre, radius, radius)  # no K 2, L 8 … on the picture: they ran into one another
            speed = 1.6 / (k + 1)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(ELECTRON if not dark else '#6ea2f0'))
            for e in range(count):
                angle = self.t * speed + 2 * pi * e / count + k * 0.7
                p.drawEllipse(QPointF(centre.x() + radius * cos(angle), centre.y() + radius * sin(angle)), 3.2, 3.2)
        # the nucleus: A balls on a disc (sunflower), Z of them protons spread evenly
        count = self.a
        ball = max(1.2, nucleus / sqrt(count) * 0.95)
        wobble = 0.6 * sin(self.t * 3)
        edge = QColor('#10151c' if dark else '#ffffff')
        protons = {int((i + 0.5) * count / self.z) for i in range(self.z)} if self.z else set()
        for i in range(count):
            r = (nucleus - ball) * sqrt((i + 0.5) / count)
            angle = i * GOLDEN
            point = QPointF(centre.x() + r * cos(angle) + wobble * cos(i),
                            centre.y() + r * sin(angle) + wobble * sin(i))
            p.setPen(QPen(edge, 0.6))
            p.setBrush(QColor(PROTON if i in protons else NEUTRON))
            p.drawEllipse(point, ball, ball)
        p.end()


class ElementsDialog(QDialog):
    """The periodic table in its frame — the groups 1–18 above, the periods 1–7 at the side, the lanthanides and the
    actinides below it with their names. A click on an element widens the window by a second frame: the atom, its
    numbers and the table of its isotopes (a row — the atom with that isotope). Every fact is a line of its own
    that never wraps, the atom is of a fixed size and the card of a fixed width — so no element makes it taller."""

    CARD_WIDTH = 450
    # the atom and the counts side by
    # side, the configuration and the shells in full lines under them; the mass and the share of the isotope are in its
    # table (its row chosen) — not repeated
    FACTS = ('Атомная масса', 'Изотоп', 'Протонов', 'Нейтронов', 'Электронов', 'Всего частиц')
    WIDE = ('Электронная конфигурация', 'Электроны по оболочкам')

    def __init__(self, parent=None, symbol=None):
        super().__init__(parent)
        from modules.compass.panels.periodic import ROWS

        self.setWindowTitle(tr('Таблица Менделеева'))
        outer = QHBoxLayout(self)
        outer.setSpacing(14)
        table = QGroupBox(tr('Периодическая система'))
        grid = QGridLayout(table)
        grid.setSpacing(3)
        self.buttons = {}

        def caption(text, tip, align):
            label = QLabel(text)
            label.setAlignment(align)
            label.setToolTip(tip)
            label.setStyleSheet('color: #7a8394;')
            return label

        centre = Qt.AlignmentFlag.AlignCenter
        for group in range(1, 19):
            grid.addWidget(caption(str(group), tr('Группа {}').format(group), centre | Qt.AlignmentFlag.AlignBottom),
                           0, group)
        for period in range(1, 8):
            grid.addWidget(caption(str(period), tr('Период {}').format(period), centre), period, 0)
        grid.setRowMinimumHeight(8, 12)  # a gap between the table and the f-block below it
        for row, entries in enumerate(ROWS):
            place = row + 1 if row < 7 else row + 2
            if row >= 7:
                name = tr('Лантаниды') if row == 7 else tr('Актиниды')
                grid.addWidget(caption(name + ':', tr('57–71') if row == 7 else tr('89–103'),
                                       Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter), place, 0, 1, 3)
            for col, item in enumerate(entries):
                if not item:
                    continue
                if item in ('*', '**'):
                    grid.addWidget(caption('57–71' if item == '*' else '89–103',
                                           tr('Лантаниды') if item == '*' else tr('Актиниды'), centre), place, col + 1)
                    continue
                button = QPushButton(f'{SYMBOLS.index(item) + 1}\n{item}')
                button.setFixedSize(40, 43)
                button.setCheckable(True)
                button.setProperty('azimuthNoIcon', True)
                family, colour = elements.CATEGORY[item]
                button.setToolTip(f'{tr(elements.NAMES[item])} — {tr(family).lower()}')
                button.setStyleSheet(f'QPushButton {{padding: 0; background: {colour}; color: #1b2230; '
                                     f'border: 1px solid {QColor(colour).darker(118).name()};}} '
                                     f'QPushButton:hover {{border: 2px solid #e2bf78;}} '
                                     'QPushButton:checked {background: #2a62b8; color: white; border-color: #2a62b8;}')
                button.clicked.connect(lambda checked=False, s=item: self.click(s))
                grid.addWidget(button, place, col + 1)
                self.buttons[item] = button
        grid.addWidget(self._legend(), 1, 3, 3, 10)  # in the gap above the transition metals, as tables have it
        outer.addWidget(table, 0, Qt.AlignmentFlag.AlignTop)

        self.card = QGroupBox()
        self.card.setFixedWidth(self.CARD_WIDTH)
        card = QGridLayout(self.card)
        card.setHorizontalSpacing(12)
        card.setVerticalSpacing(8)
        self.atom = AtomView()
        self.atom.setFixedSize(200, 200)
        card.addWidget(self.atom, 0, 0)
        facts = QGridLayout()
        facts.setVerticalSpacing(4)
        facts.setHorizontalSpacing(10)
        wide = QGridLayout()
        wide.setVerticalSpacing(4)
        wide.setHorizontalSpacing(10)
        self.facts = {}
        for layout, keys in ((facts, self.FACTS), (wide, self.WIDE)):
            for k, key in enumerate(keys):
                name = QLabel(tr(key) + ':')
                name.setStyleSheet('color: #5b6474;')
                value = QLabel()
                value.setStyleSheet('font-weight: 600;')
                value.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
                layout.addWidget(name, k, 0)
                layout.addWidget(value, k, 1)
                self.facts[key] = value
            layout.setColumnStretch(1, 1)
        card.addLayout(facts, 0, 1, Qt.AlignmentFlag.AlignVCenter)
        card.addLayout(wide, 1, 0, 1, 2)
        self.isotopes = QTableWidget(0, 3)
        self.isotopes.setHorizontalHeaderLabels([tr('Изотоп'), tr('Масса, а. е. м.'), tr('Доля')])
        self.isotopes.verticalHeader().hide()
        self.isotopes.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.isotopes.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.isotopes.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.isotopes.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.isotopes.setMinimumHeight(90)
        self.isotopes.currentCellChanged.connect(lambda row, *_: self.show_isotope(row))
        card.addWidget(self.isotopes, 2, 0, 1, 2)
        card.setRowStretch(2, 1)
        self.card.hide()  # until an element is chosen
        outer.addWidget(self.card, 0, Qt.AlignmentFlag.AlignTop)
        # the window as large as what it shows: the table alone, or the table and the card — the card as tall as the
        # table, so no element changes the height
        outer.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.table = table
        self.symbol, self.rows = None, []
        if symbol in self.buttons:
            self.show_element(symbol)

    def click(self, symbol):
        """A click on an element — its card; a second click on the same one hides the card again."""
        if symbol == self.symbol and not self.card.isHidden():
            self.hide_element()
        else:
            self.show_element(symbol)

    def hide_element(self):
        """The card hidden, the window narrower by it, no element chosen."""
        for button in self.buttons.values():
            button.setChecked(False)
        self.symbol = None
        self.card.hide()  # the window narrower by it (its fixed-size layout)

    def _legend(self):
        """The families and their colours, two columns."""
        legend = QWidget()
        rows = QGridLayout(legend)
        rows.setContentsMargins(6, 4, 6, 4)
        rows.setHorizontalSpacing(6)
        rows.setVerticalSpacing(3)
        half = (len(elements.CATEGORIES) + 1) // 2
        for k, (name, colour, _) in enumerate(elements.CATEGORIES):
            swatch = QLabel()
            swatch.setFixedSize(14, 14)
            swatch.setStyleSheet(f'background: {colour}; border: 1px solid {QColor(colour).darker(125).name()}; '
                                 'border-radius: 3px;')
            label = QLabel(tr(name))
            label.setStyleSheet('font-size: 12px;')
            rows.addWidget(swatch, k % half, 3 * (k // half))
            rows.addWidget(label, k % half, 3 * (k // half) + 1)
        rows.setColumnMinimumWidth(2, 18)
        rows.setColumnStretch(5, 1)
        return legend

    def _keep_on_screen(self):
        """The window wider by the card — moved left when its right edge would leave the screen."""
        screen = self.screen()
        if screen is None or not self.isVisible():
            return
        room, frame = screen.availableGeometry(), self.frameGeometry()
        if frame.right() > room.right():
            self.move(max(room.left(), self.x() - (frame.right() - room.right())), self.y())

    def fact(self, key):
        return self.facts[key].text()

    def _widen(self):
        """The card shown: the window grows by it (its fixed-size layout), kept on the screen."""
        if self.card.isHidden():
            self.card.setFixedHeight(self.table.height() if self.isVisible() else self.table.sizeHint().height())
            self.card.show()
            QTimer.singleShot(0, self._keep_on_screen)

    def show_element(self, symbol):
        """The card of the element: its most abundant isotope first (or its most stable one)."""
        for key, button in self.buttons.items():
            button.setChecked(key == symbol)
        self.symbol = symbol
        z = SYMBOLS.index(symbol) + 1
        self.card.setTitle(f'{tr(elements.NAMES[symbol])} · {symbol} · Z = {z}')
        self.rows = list(STABLE.get(symbol, ()))
        self.isotopes.blockSignals(True)
        self.isotopes.setRowCount(len(self.rows) or 1)
        if self.rows:
            for k, (number, mass, share) in enumerate(self.rows):
                for j, value in enumerate((str(number).translate(SUPERSCRIPT) + symbol, f'{mass:.6f}',
                                           f'{share * 100:.4g} %')):
                    self.isotopes.setItem(k, j, QTableWidgetItem(value))
            main = max(range(len(self.rows)), key=lambda k: self.rows[k][2])
        else:
            longest = elements.LONGEST.get(symbol, round(2.5 * z))
            self.isotopes.setItem(0, 0, QTableWidgetItem(str(longest).translate(SUPERSCRIPT) + symbol))
            self.isotopes.setItem(0, 1, QTableWidgetItem('—'))
            self.isotopes.setItem(0, 2, QTableWidgetItem(tr('нет в природе')))
            main = 0
        for k in range(self.isotopes.rowCount()):
            for j in range(3):
                self.isotopes.item(k, j).setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        self.isotopes.blockSignals(False)
        self.isotopes.setCurrentCell(main, 0)
        self.show_isotope(main)
        self._widen()
        return z

    def show_isotope(self, row):
        """The atom and the numbers of the isotope of that row."""
        symbol = self.symbol
        z = SYMBOLS.index(symbol) + 1
        if self.rows and 0 <= row < len(self.rows):
            number = self.rows[row][0]
        else:
            number = elements.LONGEST.get(symbol, round(2.5 * z))
        average = elements.mean_mass(symbol)
        self.atom.set_atom(z, number)
        values = {
            'Атомная масса': f'{average:.4f}' if average is not None else f'[{number}]',
            'Изотоп': str(number).translate(SUPERSCRIPT) + symbol,
            'Протонов': str(z), 'Нейтронов': str(number - z), 'Электронов': str(z), 'Всего частиц': str(number + z),
            'Электронная конфигурация': elements.text(z),
            'Электроны по оболочкам': ' '.join(f'{SHELLS[k]}{c}' for k, c in enumerate(elements.shells(z))),
        }
        for key, value in values.items():
            self.facts[key].setText(value)
        return number
