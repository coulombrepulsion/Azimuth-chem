"""The small windows of a calculation in Sextant: the output of the program (OutputWindow), «Дополнительные
настройки…» (OptionsDialog), the picker of methods and basis sets by family (FamilyPicker).

Split off modules/sextant/job_window.py (0.222.30); job_window still names them.
"""

import os
import time
from PySide6.QtCore import QEvent, QPoint, Qt, QTimer, QUrl
from PySide6.QtGui import QDesktopServices, QFont, QIcon, QTextCursor
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QSpinBox,
    QDialog,
    QLineEdit,
    QFrame,
    QScrollArea,
    QSizePolicy,
    QMenu,
    QPushButton,
    QFormLayout,
    QHBoxLayout,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)
from azimuth.i18n import tr
from azimuth.ui import button, card, icon_button, label, smooth


SHOWN_BYTES = 8_000_000  # the end of a bigger output is shown


def gold_star(side=14):
    """A gold star (hub.branding.STAR_GOLD, as the star of the icons) — the mark of the recommended item."""
    import math

    from PySide6.QtCore import QPointF
    from PySide6.QtGui import QColor, QPainter, QPixmap, QPolygonF

    from hub.branding import STAR_GOLD

    ratio = 2
    pixmap = QPixmap(side * ratio, side * ratio)
    pixmap.setDevicePixelRatio(ratio)
    pixmap.fill(Qt.GlobalColor.transparent)
    p = QPainter(pixmap)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(STAR_GOLD['light']))
    c, outer, inner = side / 2, side / 2 - 0.5, side / 5
    p.drawPolygon(QPolygonF([QPointF(c + (outer if k % 2 == 0 else inner) * math.sin(math.pi * k / 5),
                                     c - (outer if k % 2 == 0 else inner) * math.cos(math.pi * k / 5)) for k in range(10)]))
    p.end()
    return QIcon(pixmap)


class OutputWindow(QWidget):
    """The output file of the program as it is written — not a copy of its end: the whole file (up to
    SHOWN_BYTES), the new lines added once a second, a search, «Открыть в редакторе»."""

    def __init__(self, owner):
        super().__init__(owner, Qt.WindowType.Window)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName('workspace')
        self.setWindowTitle(tr('Вывод программы'))
        self.paths = ()
        self.path = None
        self.offset = 0
        self.changed = 0.0
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.follow = QCheckBox(tr('Следить за концом'))
        self.follow.setChecked(True)
        self.follow.toggled.connect(lambda on: on and self.to_end())
        self.find = QLineEdit()
        self.find.setPlaceholderText(tr('Найти в выводе (Enter — дальше)'))
        self.find.setClearButtonEnabled(True)
        self.find.returnPressed.connect(self.find_next)
        self.editor_button = icon_button(tr('Открыть в редакторе'), self.open_in_editor, 'file-open')
        row.addWidget(self.follow)
        row.addWidget(self.find, 1)
        row.addWidget(self.editor_button)
        layout.addLayout(row)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setObjectName('code')
        self.view.setFont(QFont('Menlo', 11))
        self.view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.view.verticalScrollBar().valueChanged.connect(self._scrolled)
        layout.addWidget(self.view, 1)
        self.info = label('', 'subtitle')
        layout.addWidget(self.info)
        self.timer = QTimer(self)
        self.timer.setInterval(1000)
        self.timer.timeout.connect(self.refresh)
        self.resize(820, 620)

    def watch(self, paths):
        """Show the first file of paths that exists (Gaussian, Psi4: the output appears after their stdout)."""
        self.paths = tuple(p for p in paths if p is not None)
        self.path = None
        self.offset = 0
        self.view.clear()
        self.refresh()
        self.show()
        self.raise_()
        self.activateWindow()
        self.timer.start()
        return self

    def _pick(self):
        for path in self.paths:
            if os.path.exists(path):
                return path
        return None

    def refresh(self):
        if not self.isVisible() and self.timer.isActive() and self.path is not None:
            self.timer.stop()  # hidden: nothing to follow
            return False
        path = self._pick()
        if path is None:
            self.info.setText(tr('Файл вывода ещё не создан — программа только запускается.'))
            return False
        if path != self.path:
            self.path, self.offset = path, 0
            self.view.clear()
            self.setWindowTitle(tr('Вывод программы') + ' — ' + os.path.basename(str(path)))
        try:
            size = os.path.getsize(path)
            if size < self.offset:  # written anew
                self.offset = 0
                self.view.clear()
            if size == self.offset:
                self._tell(size)
                return False
            with open(path, 'rb') as f:
                start = self.offset if self.offset else max(0, size - SHOWN_BYTES)
                f.seek(start)
                data = f.read(size - start)
        except OSError as exc:
            self.info.setText(str(exc))
            return False
        text = data.decode('utf-8', errors='replace')
        if not self.offset and start:
            text = tr('… показан конец файла …') + '\n' + text.split('\n', 1)[-1]
        self.offset = size
        self.changed = time.time()
        bar = self.view.verticalScrollBar()
        at_end = bar.value() >= bar.maximum() - 2
        cursor = QTextCursor(self.view.document())
        cursor.movePosition(QTextCursor.MoveOperation.End)
        cursor.insertText(text)
        if self.follow.isChecked() and at_end:
            self.to_end()
        self._tell(size)
        return True

    def _tell(self, size):
        when = time.strftime('%H:%M:%S', time.localtime(self.changed)) if self.changed else '—'
        self.info.setText(tr(f'{self.path} · {size / 1024:.0f} КБ · изменён в {when}'))

    def to_end(self):
        bar = self.view.verticalScrollBar()
        bar.setValue(bar.maximum())

    def _scrolled(self, value):
        bar = self.view.verticalScrollBar()
        if value < bar.maximum() - 2 and self.follow.isChecked() and self.view.underMouse():
            self.follow.blockSignals(True)  # scrolled up by the user: stop following until switched on again
            self.follow.setChecked(False)
            self.follow.blockSignals(False)

    def find_next(self):
        text = self.find.text()
        if not text:
            return False
        if self.view.find(text):
            return True
        cursor = self.view.textCursor()  # from the top again
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.view.setTextCursor(cursor)
        return self.view.find(text)

    def open_in_editor(self):
        if self.path is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(self.path)))

    def showEvent(self, event):
        super().showEvent(event)
        if self.paths and not self.timer.isActive():
            self.timer.start()


class OptionsDialog(QDialog):
    """rows: (title, widget); (title, None) starts a group. The groups are sections of a list on the left and
    their pages on the right in a card, the window of one fixed size (the folding groups of 0.48.0 – 0.72 made it grow
    and shrink: on macOS it went over the edge of the screen and showed black squares above while resizing); opened —
    the number of the section shown first."""

    WIDTH, HEIGHT = 820, 400  # wider — the long switches and the arrows of the fields were cut off (was 700 ×
    # 480); 900 — the Windows fonts are wider; 820 × 400 — four short sections are left (optimization
    # and TD-DFT went into the form), the window was mostly empty

    def __init__(self, owner, rows, note='', opened=0):
        from PySide6.QtWidgets import QListWidget, QStackedWidget

        super().__init__(owner)
        self.setWindowTitle(tr('Дополнительные настройки расчёта'))
        self.setObjectName('workspace')  # the background of the sections of the program
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)
        body_row = QHBoxLayout()
        body_row.setSpacing(14)
        self.sections = QListWidget()
        self.sections.setObjectName('optionSections')
        self.sections.setFixedWidth(200)
        self.sections.setFrameShape(QFrame.Shape.NoFrame)
        self.sections.setStyleSheet(
            'QListWidget#optionSections {background: transparent; outline: none;}'
            'QListWidget#optionSections::item {padding: 8px 10px; border-radius: 8px; margin: 1px 0;}'
            'QListWidget#optionSections::item:selected {background: #2a62b8; color: white;}')
        body_row.addWidget(self.sections)
        frame, card_layout = card('')
        self.page_title = card_layout.itemAt(0).widget()
        self.pages = QStackedWidget()
        card_layout.addWidget(self.pages, 1)
        body_row.addWidget(frame, 1)
        outer.addLayout(body_row, 1)
        self.groups = []  # (title, page) — 0.73.0 (were heading buttons and folding bodies)
        self.forms = []  # the forms of the sections (the crystal page hides rows of one program)
        form = None
        for title, widget in rows:
            if widget is None or form is None:
                page = QWidget()
                column = QVBoxLayout(page)
                column.setContentsMargins(0, 0, 0, 0)
                form = QFormLayout()
                form.setSpacing(12)
                form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
                self.forms.append(form)
                column.addLayout(form)
                column.addStretch(1)
                scroll = QScrollArea()  # a long section scrolls inside its page; the window keeps its size
                scroll.setWidgetResizable(True)
                scroll.setFrameShape(QFrame.Shape.NoFrame)
                scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
                scroll.setStyleSheet('QScrollArea {background: transparent; border: none;}')
                scroll.viewport().setAutoFillBackground(False)
                page.setObjectName('optionsPage')
                page.setStyleSheet('QWidget#optionsPage {background: transparent;}')
                scroll.setWidget(page)
                name = title if widget is None else tr('Общие')
                self.pages.addWidget(scroll)
                self.sections.addItem(name)
                self.groups.append((name, page))
                if widget is None:
                    continue
            if isinstance(widget, (QSpinBox, QDoubleSpinBox)):  # the value in the middle, as in the form
                widget.setAlignment(Qt.AlignmentFlag.AlignCenter)
            if isinstance(widget, QComboBox):
                # a list no wider than the page — on Windows (Segoe UI) «Очень строгая (VeryTight)» made the
                # list of the SCF 436 px on a page of 375 and its end went under the edge; the open list keeps the
                # whole names
                widget.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
                widget.setMinimumContentsLength(12)
                widget.setSizePolicy(QSizePolicy.Policy.Expanding, widget.sizePolicy().verticalPolicy())
            if title:
                form.addRow(title, widget)
            else:  # a switch takes the whole width of the page (its text was cut at the edge)
                # never wider than the page — on Windows its text (Segoe UI) asked 2 px more than the page had,
                # and the page itself grew past the window
                widget.setSizePolicy(QSizePolicy.Policy.Ignored, widget.sizePolicy().verticalPolicy())
                form.addRow(widget)
        if note:
            self.note = label(note, 'subtitle')
            self.note.setWordWrap(True)
            outer.addWidget(self.note)
        self.sections.currentRowChanged.connect(self.show_section)
        self.buttons_row = row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(button(tr('Готово'), self.close))  # what closes is white
        outer.addLayout(row)
        self.setFixedSize(self.WIDTH, self.HEIGHT)
        # the list as wide as its longest section («Возбуждённые состояния (TD-DFT)» was cut, with a scroll bar)
        self.sections.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.sections.setFixedWidth(max(200, self.sections.sizeHintForColumn(0) + 28))
        self.sections.setCurrentRow(max(0, min(opened, len(self.groups) - 1)))

    def show_section(self, index):
        if 0 <= index < len(self.groups):
            self.pages.setCurrentIndex(index)
            self.page_title.setText(self.groups[index][0])

    def current_section(self):
        index = self.sections.currentRow()
        return self.groups[index][0] if 0 <= index < len(self.groups) else ''

    def open_group(self, title):
        """Show the section with this title; its page."""
        for index, (name, page) in enumerate(self.groups):
            if name == title:
                self.sections.setCurrentRow(index)
                return page
        return None


def rounded(menu):
    """A menu drawn with the rounded corners of the style sheet — no square window behind them."""
    menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
    menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint)
    return menu


class FamilyPicker(QPushButton):
    """The method or the basis set chosen through families — a short menu of families (Хартри — Фок,
    DFT: гибридные …, Попла, def2 …), each opening the list of its items. The data stay in the combo box it shows
    (the bold unselectable headers of fill_grouped are the families), which keeps its API for the program and the
    tests; the button follows its current item and whether it is enabled."""

    def __init__(self, combo, parent=None):
        super().__init__(parent)
        self.combo = combo
        self.setObjectName('picker')
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        combo.currentIndexChanged.connect(self.sync)
        combo.installEventFilter(self)
        self.clicked.connect(self.open_menu)
        self.menu = None
        self.recommended = None  # (data, text, apply) — the first item of the menu, also in the tooltip
        self.sync()

    def sync(self, *args):
        self.setText(self.combo.currentText())
        self.setEnabled(self.combo.isEnabled())

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.EnabledChange:
            self.setEnabled(watched.isEnabled())
        return False

    def build_menu(self):
        menu = smooth(QMenu(self))
        rounded(menu)  # rounded corners, as the other menus (the square ones of the window showed)
        current = self.combo.currentIndex()
        if self.recommended is not None:
            data, text, apply = self.recommended
            item = menu.addAction(gold_star(), text)  # the gold of the icons — the star of the advice
            item.setObjectName('recommended')
            item.setEnabled(self.combo.currentData() != data or apply is not None)
            item.triggered.connect(lambda checked=False: apply() if apply else self.combo.setCurrentIndex(self.combo.findData(data)))
            menu.addSeparator()
        target = menu
        for i in range(self.combo.count()):
            text = self.combo.itemText(i)
            if self.combo.itemData(i) is None:  # a family
                target = rounded(smooth(menu.addMenu(text)))
                continue
            action = target.addAction(text)
            action.setCheckable(True)
            action.setChecked(i == current)
            if i == current and target is not menu:
                target.menuAction().setText('● ' + target.title())
            action.triggered.connect(lambda checked=False, i=i: self.combo.setCurrentIndex(i))
        return menu

    def open_menu(self):
        """A press on the button while its menu is open closes the menu, and on Windows the press goes on to
        the button — its click opened the menu again. A click within CLOSED_JUST of the closing is that same press:
        the menu stays closed (on macOS the press is not passed on, nothing changes there)."""
        import time

        if time.monotonic() - self._closed_at < self.CLOSED_JUST and self.underMouse():
            self._closed_at = 0.0
            return None
        self.menu = self.build_menu()
        self.menu.aboutToHide.connect(self._menu_closed)
        self.menu.popup(self.mapToGlobal(QPoint(0, self.height() + 2)))
        return self.menu

    CLOSED_JUST = 0.3
    _closed_at = 0.0

    def _menu_closed(self):
        import time

        self._closed_at = time.monotonic()
