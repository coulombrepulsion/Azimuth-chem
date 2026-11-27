"""The search of the menus and the buttons in the side panel: a magnifier in a rounded square over the languages; the field
slides out of the square to the right, the results are listed over it.

§0 STATE
    0.248.0 (2026-11-27, the owner: «Лупа пусть будет расположена в левой панели над языком, в виде иконки внутри
    квадратика со скругленными краями, и при нажатии поле выдвигается из квадратика»). Until then the magnifier stood
    at the right end of the row of the menus (0.244.0) and before that in «Справка».
§1 PURPOSE
    What hub/menu_search.py finds (the items of the menus of the section shown and the buttons of the window), asked
    from the side panel in every section.
§2 ALGORITHM
    The magnifier is a button of the column of the panel as the others (QPushButton#nav, 0.248.3).
    A press anywhere but on the field, its list and the button puts the field away (an event filter of the
    application while it is out). open(): the panel (a frame over the page, a child of
    the window) takes the place of the square and grows to the right to WIDTH px in SLIDE ms; the field in it gets the
    cursor. A word typed lists the results (menu_search.find, LIMIT) in a list over the field — the square stands at
    the bottom of the window. Enter or a click — the result shown where it is (menu_search.reveal); Up and Down move in
    the list; Escape, a click elsewhere or the result chosen — the panel slides back into the square.
§4 SPECIFICATION
    SidebarSearch(hub, parent): button (QPushButton), panel (QFrame), field (QLineEdit), results (QListWidget),
    found ([menu_search.Entry]); open(animate=True), close(animate=True), is_open(), set_dark(dark), choose(row);
    picture_of(entry) -> QIcon | None — the icon shown beside a result (0.248.5).
§7 TESTS
    tests/hub/test_menu_search.py.
"""

from PySide6.QtCore import QEasingCurve, QEvent, QObject, QPoint, QRect, QSize, Qt, QTimer, QVariantAnimation
from PySide6.QtWidgets import QApplication, QFrame, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QPushButton

from azimuth.i18n import tr

WIDTH = 380  # px: the panel with the field slid out
SLIDE = 170  # ms
ROW = 28  # px: a row of the results
TITLE = 'Поиск по меню и кнопкам'


class SidebarSearch(QObject):
    def __init__(self, hub, parent):
        super().__init__(parent)
        self.hub = hub
        self.found = []
        self.dark = False
        # a button of the panel as the theme, the settings and «О программе» (0.248.3, the owner: «у лупы при наведении
        # отличается область выделения, от других иконок на панели»): QPushButton#nav, the whole width of the column
        self.button = QPushButton(parent)
        self.button.setObjectName('nav')
        self.button.setIconSize(QSize(22, 22))
        self.button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.button.setToolTip(tr(TITLE))
        self.button.setAccessibleName(tr(TITLE))
        self.button.clicked.connect(lambda: self.close() if self.is_open() else self.open())
        self.panel = QFrame(hub)  # over the page and over the panel, a child of the window
        self.panel.setObjectName('sideSearchPanel')
        self.panel.hide()
        row = QHBoxLayout(self.panel)
        row.setContentsMargins(48, 4, 8, 4)  # set again when it opens: the field begins where the button ends
        self.field = QLineEdit(self.panel)
        self.field.setObjectName('sideSearchField')
        self.field.setPlaceholderText(tr(TITLE))
        self.field.setClearButtonEnabled(True)
        row.addWidget(self.field)
        # the magnifier stays where it was: a button of the same style as that of the panel (its icon as far from the
        # left), 0.248.4 — it moved to the middle when the panel opened
        self.glass = QPushButton(self.panel)
        self.glass.setObjectName('nav')
        self.glass.setIconSize(QSize(22, 22))
        self.glass.move(0, 0)
        self.glass.clicked.connect(lambda: self.close())
        self.results = QListWidget(hub)
        self.results.setObjectName('sideSearchResults')
        self.results.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.results.setUniformItemSizes(True)
        self.results.setIconSize(QSize(18, 18))
        self.results.hide()
        self.results.itemClicked.connect(lambda item: self.choose(self.results.row(item)))
        self.field.textChanged.connect(self._fill)
        self.field.installEventFilter(self)
        self.motion = QVariantAnimation(self)
        self.motion.setDuration(SLIDE)
        self.motion.setEasingCurve(QEasingCurve.Type.InOutCubic)
        self.motion.valueChanged.connect(self._grow)
        self.motion.finished.connect(self._moved)
        self._opening = False
        self.set_dark(False)

    # -- the look ----------------------------------------------------------------------------------------------
    def set_dark(self, dark):
        from azimuth.icons import icon

        self.dark = bool(dark)
        ink = '#c9d3e2' if dark else '#3f4d61'
        line = 'rgba(255, 255, 255, 0.16)' if dark else 'rgba(27, 34, 48, 0.16)'
        back = '#1a2130' if dark else '#ffffff'
        text = '#e8ecf3' if dark else '#1b2230'
        accent = '#6ea2f0' if dark else '#2a62b8'
        # as the other buttons of the panel: no frame, a light ground under the mouse (0.248.1, the owner: «Убери вокруг
        # лупы рамку, пусть будет как другие кнопки на панели»)
        self.glass.setStyleSheet('QPushButton#nav, QPushButton#nav:hover {background: transparent; border: none;}')
        for button in (self.button, self.glass):
            button.setIcon(icon('search', ink))
        self.panel.setStyleSheet(
            f'QFrame#sideSearchPanel {{background: {back}; border: 1px solid {accent}; border-radius: 10px;}}'
            f'QLineEdit#sideSearchField {{border: none; background: transparent; color: {text}; font-size: 13px;}}')
        self.results.setStyleSheet(
            f'QListWidget#sideSearchResults {{background: {back}; border: 1px solid {line}; border-radius: 10px;'
            f' color: {text}; padding: 4px; font-size: 13px;}}'
            f'QListWidget#sideSearchResults::item {{padding: 4px 8px; border-radius: 6px;}}'
            f'QListWidget#sideSearchResults::item:selected {{background: {accent}; color: white;}}')

    # -- opening and closing -----------------------------------------------------------------------------------
    def is_open(self):
        return self.panel.isVisible() and (self._opening or self.motion.state() != QVariantAnimation.State.Running)

    def _place(self):
        """Where the button is seen, in the coordinates of the window: the column of the panel is as wide as the open
        panel, the rail shows its left part only (0.248.4: the field began far to the right of the magnifier)."""
        place = QRect(self.button.mapTo(self.hub, QPoint(0, 0)), self.button.size())
        sidebar = getattr(self.hub, 'sidebar', None)
        if sidebar is not None and sidebar.isVisible():
            left = self.button.mapTo(sidebar, QPoint(0, 0)).x()
            place.setWidth(max(1, min(place.width(), sidebar.width() - 2 * left)))
        return place

    def open(self, animate=True):
        if self.is_open():
            self.field.setFocus()
            return
        place = self._place()
        self.panel.setGeometry(place)
        self.glass.setFixedSize(place.size())
        self.panel.layout().setContentsMargins(place.width(), 4, 8, 4)  # the field begins where the button ends
        QApplication.instance().installEventFilter(self)  # a click anywhere else puts the field away
        self.panel.show()
        self.panel.raise_()
        self._opening = True
        if animate:
            self.motion.stop()
            self.motion.setStartValue(float(place.width()))
            self.motion.setEndValue(float(WIDTH))
            self.motion.start()
        else:
            self._grow(float(WIDTH))
            self._moved()
        self.field.setFocus()

    def close(self, animate=True):
        if not self.panel.isVisible():
            return
        self.results.hide()
        self._opening = False
        app = QApplication.instance()
        if app is not None:
            app.removeEventFilter(self)
        if animate:
            # into the part of the button that is seen (0.248.6: it went to the width of the whole column and then
            # vanished — the folding looked torn); the field hidden at once, the frame slides alone
            self.field.hide()
            self.motion.stop()
            self.motion.setStartValue(float(self.panel.width()))
            self.motion.setEndValue(float(self._place().width()))
            self.motion.start()
        else:
            self._moved()

    def _grow(self, width):
        place = self._place()
        self.panel.setGeometry(place.left(), place.top(), round(width), place.height())
        self._place_results()

    def _moved(self):
        if not self._opening:
            self.panel.hide()
            self.field.show()
            self.field.blockSignals(True)
            self.field.clear()
            self.field.blockSignals(False)
            self.found = []
            self.results.clear()

    # -- the results -------------------------------------------------------------------------------------------
    def _fill(self, text):
        from hub import menu_search

        header = getattr(self.hub, 'header', None)
        self.found = menu_search.find(menu_search.entries(header, getattr(self.hub, 'studio', None)), text) if header else []
        self.results.clear()
        if text.strip() and not self.found:
            item = QListWidgetItem(tr('Ничего не найдено'))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.results.addItem(item)
        for entry in self.found:
            item = QListWidgetItem(entry.label())
            picture = picture_of(entry)
            if picture is not None:
                item.setIcon(picture)  # a button or an item with an icon — the icon beside the words (0.248.5)
            if entry.tip:
                item.setToolTip(entry.tip)
            self.results.addItem(item)
        if self.found:
            self.results.setCurrentRow(0)
        self.results.setVisible(bool(text.strip()))
        self._place_results()

    def _place_results(self):
        if not self.results.isVisible():
            return
        place = self.panel.geometry()
        count = max(1, self.results.count())
        row = self.results.sizeHintForRow(0) if self.results.count() else 0
        row = row if row > 0 else ROW
        # as tall as its rows (0.248.6: the estimate of ROW px a row left an empty band under the results)
        height = min(count, menu_limit()) * row + 2 * self.results.frameWidth() + 10
        width = max(WIDTH, min(560, self.results.sizeHintForColumn(0) + 32))
        top = place.top() - height - 6  # over the field: the square stands low in the window
        if top < 8:
            top = place.bottom() + 6
        self.results.setGeometry(place.left(), top, width, height)
        self.results.raise_()

    def choose(self, row):
        """The result of the row shown where it is (the panel slides back first)."""
        from hub import menu_search

        if not 0 <= row < len(self.found):
            return None
        entry = self.found[row]
        self.close()
        QTimer.singleShot(SLIDE + 40, lambda: menu_search.reveal(self.hub.header, entry))
        return entry

    def _inside(self, event):
        """The press is on the field, its list or the button of the search."""
        point = event.globalPosition().toPoint()
        for widget in (self.panel, self.results, self.button):
            if widget.isVisible() and widget.rect().contains(widget.mapFromGlobal(point)):
                return True
        return False

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.MouseButtonPress and self.panel.isVisible() and self._opening:
            if not self._inside(event):  # a click on the panel, the page or anywhere else (0.248.3)
                self.close()
            return False
        if watched is self.field and event.type() == QEvent.Type.KeyPress:
            key = event.key()
            if key == Qt.Key.Key_Escape:
                self.close()
                return True
            if key in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
                self.choose(max(0, self.results.currentRow()))
                return True
            if key in (Qt.Key.Key_Down, Qt.Key.Key_Up) and self.found:
                step = 1 if key == Qt.Key.Key_Down else -1
                self.results.setCurrentRow((self.results.currentRow() + step) % len(self.found))
                return True
        if watched is self.field and event.type() == QEvent.Type.FocusOut:
            QTimer.singleShot(150, self._lost)
        return False

    def _lost(self):
        """A click elsewhere: the field gave up the cursor and no result is being chosen."""
        if self.panel.isVisible() and self._opening and not self.field.hasFocus() and not self.results.underMouse():
            self.close()


def picture_of(entry):
    """The icon of what a result names: that of its button or of its item of a menu; None when it has none."""
    for source in (entry.widget, entry.action):
        if source is None:
            continue
        try:
            picture = source.icon()
        except (AttributeError, RuntimeError):  # deleted since the search, or without icons
            continue
        if picture is not None and not picture.isNull():
            return picture
    return None


def menu_limit():
    from hub import menu_search

    return menu_search.LIMIT
