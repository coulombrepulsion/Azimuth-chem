"""The small windows of the styles of the model: «Стиль подписей…», «Стиль измерений…», «Стиль векторов и
плоскостей…».

§1 PURPOSE
    One form for the three, close to Chemcraft: the colour in a
    circle (ColourDot) with ↺ beside it — the colour of the program back (its tip says what that is), the colour
    picker of Qt (in the theme of the program: the one of macOS follows the system and was dark in a light program),
    a list of the fonts, number fields with their numbers in the middle, the names of the rows on the line of the
    middle of their fields.
§2 INTERFACE
    pick_colour(initial, parent, title) -> '#rrggbb' or None; ColourDot(value, standard, tip) — value '' or #rrggbb,
    standard() the colour shown for '' (the theme may change it; a pair — a circle of two halves); font_box(family) and
    family_of(box); number(low, high, step, decimals, suffix, value); styled_form(box) -> QFormLayout.
"""

from PySide6.QtCore import QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFontDatabase, QPainter, QPen
from PySide6.QtWidgets import (QAbstractSpinBox, QComboBox, QDoubleSpinBox, QFormLayout, QHBoxLayout, QPushButton,
                               QSpinBox, QToolButton, QWidget)

from azimuth.i18n import tr

DOT = 26  # px of the circle of a colour


def pick_colour(initial, parent, title):
    """The colour picker of Qt, not of the system: drawn in the theme of the program (its compact look — the QSS of
    azimuth/app.py, «QColorDialog …»). The colour chosen (#rrggbb), or None."""
    from PySide6.QtWidgets import QColorDialog, QDialog

    load_custom_colours()
    start = QColor(initial or '')
    if not start.isValid():  # no colour yet — a grey
        start = QColor('#788897')
    dialog = QColorDialog(start, parent)
    dialog.setWindowTitle(title)
    dialog.setOption(QColorDialog.ColorDialogOption.DontUseNativeDialog, True)
    tidy_colour_dialog(dialog)
    accepted = dialog.exec() == QDialog.DialogCode.Accepted
    keep_custom_colours()  # «Добавить в набор» counts even when the window is cancelled
    if not accepted:
        return None
    colour = dialog.selectedColor()
    return colour.name() if colour.isValid() else None


# the 48 basic colours as 8 columns — grey, red, orange, yellow, green, cyan, blue, violet — of 6 lightnesses, light at
# the top
BASIC_HUES = (None, 0, 28, 52, 120, 185, 220, 275)
BASIC_LIGHTNESS = (0.88, 0.74, 0.60, 0.46, 0.32, 0.18)


def basic_colours():
    """[QColor] × 48 in the order of QColorDialog.setStandardColor — by column (index = column × 6 + row)."""
    colours = []
    for hue in BASIC_HUES:
        for k, light in enumerate(BASIC_LIGHTNESS):
            if hue is None:  # white to black
                level = round(255 * (1 - k / (len(BASIC_LIGHTNESS) - 1)))
                colours.append(QColor(level, level, level))
            else:
                colours.append(QColor.fromHslF(hue / 360, 0.75, light))
    return colours


def sort_basic_colours():
    from PySide6.QtWidgets import QColorDialog

    for index, colour in enumerate(basic_colours()):
        QColorDialog.setStandardColor(index, colour)


CUSTOM_KEY = 'custom_colours'


def load_custom_colours():
    """Every colour of the program is chosen in this one window (pick_colour); its own colours
    are one set (QColorDialog keeps them for the whole program) and are kept in the settings between starts."""
    from PySide6.QtWidgets import QColorDialog

    from azimuth.settings import open_settings

    try:
        saved = open_settings().value(CUSTOM_KEY, '') or ''
    except Exception:  # noqa: BLE001 — the colours of the user are a convenience
        return
    for index, name in enumerate(str(saved).split(',')[:QColorDialog.customCount()]):
        colour = QColor(name.strip())
        if colour.isValid():
            QColorDialog.setCustomColor(index, colour)


def keep_custom_colours():
    from PySide6.QtWidgets import QColorDialog

    from azimuth.settings import open_settings

    names = [QColorDialog.customColor(k).name() for k in range(QColorDialog.customCount())]
    try:
        open_settings().setValue(CUSTOM_KEY, ','.join(names))
    except Exception:  # noqa: BLE001
        pass


def tidy_colour_dialog(dialog):
    """The picker of Qt laid out evenly — the field «HTML» as wide as
    the number fields, not to the edge; «Взять цвет с экрана» and «Добавить к пользовательским цветам» as wide as
    their words; the left column from the top, without the empty band between the
    two groups of colours; then laid anew (relaid_colour_dialog)."""
    from PySide6.QtWidgets import (QAbstractSpinBox, QDialogButtonBox, QLineEdit, QPushButton, QSizePolicy, QSpinBox)

    sort_basic_colours()
    dialog.ensurePolished()
    spins = [s for s in dialog.findChildren(QSpinBox)]
    width = max([s.sizeHint().width() for s in spins] + [96])
    for field in dialog.findChildren(QLineEdit):
        if not isinstance(field.parentWidget(), QAbstractSpinBox):  # the field «HTML»
            field.setFixedWidth(width)
    boxes = dialog.findChildren(QDialogButtonBox)
    for button in dialog.findChildren(QPushButton):
        if any(box.isAncestorOf(button) for box in boxes):
            continue
        button.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    for button in dialog.findChildren(QPushButton):
        if button.sizePolicy().horizontalPolicy() == QSizePolicy.Policy.Fixed:
            button.setFixedWidth(button.sizeHint().width())
    relaid_colour_dialog(dialog)
    dialog.adjustSize()
    return dialog


def relaid_colour_dialog(dialog):
    """The picker of Qt laid out anew — the swatches (basic and own, their buttons) in a column on the
    left, the field of hues beside them as tall as that column and as wide as the rest of the window, the strip of
    brightness at its edge; the numbers (QColorShower) in one row under both; the buttons under them. Qt put the field
    of hues of a fixed size in a column of its own above the numbers, with a stretch beside it and between the groups of
    swatches — the empty places. The widgets are the same (taken out of the layout of Qt and put in this one); when one
    of them is not found (another version of Qt) the window stays as Qt made it. True when laid anew."""
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import (QDialogButtonBox, QHBoxLayout, QLabel, QPushButton, QSizePolicy, QVBoxLayout,
                                   QWidget)

    def kind(widget):
        return widget.metaObject().className().rsplit(':', 1)[-1]

    widgets = dialog.findChildren(QWidget)
    picker = next((w for w in widgets if kind(w) == 'QColorPicker'), None)
    strip = next((w for w in widgets if kind(w) == 'QColorLuminancePicker'), None)
    shower = next((w for w in widgets if kind(w) == 'QColorShower'), None)
    wells = [w for w in widgets if kind(w) == 'QColorWell']
    box = dialog.findChild(QDialogButtonBox)
    own_buttons = [b for b in dialog.findChildren(QPushButton) if box is None or not box.isAncestorOf(b)]
    own_buttons = [b for b in own_buttons if shower is None or not shower.isAncestorOf(b)]
    labels = {}
    for label in dialog.findChildren(QLabel):
        buddy = label.buddy()
        if buddy in wells:
            labels[wells.index(buddy)] = label
    if None in (picker, strip, shower, box) or len(wells) < 2 or len(own_buttons) < 2 or len(labels) < 2:
        return False
    basic, custom = wells[0], wells[1]  # made in this order by Qt
    if basic.sizeHint().height() < custom.sizeHint().height():
        basic, custom = custom, basic
    eye, add = own_buttons[0], own_buttons[-1]
    if add.text().count(' ') < eye.text().count(' '):  # «Добавить к пользовательским цветам» has more words
        eye, add = add, eye
    keep = [labels[wells.index(basic)], basic, eye, labels[wells.index(custom)], custom, add, picker, strip, shower, box]
    hidden = {w: w.isHidden() for w in dialog.findChildren(QWidget) if w.parentWidget() is dialog}
    old = dialog.layout()
    # the layout of Qt and its widgets go to a hidden holder in the window — kept, not deleted: Qt may still reach its
    # layouts and its other widgets (the line «Курсор …» of «Взять цвет с экрана»)
    holder = QWidget(dialog)
    holder.hide()
    holder.setLayout(old)
    rest = [w for w in hidden if w not in keep and w is not holder]
    # the swatches first; «Выбрать вручную» opens, to their right, the
    # field of hues with its strip of brightness, the numbers under it, «Взять цвет с экрана» and «Добавить в набор»
    layout = QVBoxLayout(dialog)
    layout.setContentsMargins(16, 14, 16, 14)
    layout.setSpacing(12)
    top = QHBoxLayout()
    top.setSpacing(18)
    left = QVBoxLayout()
    left.setSpacing(6)
    basic_label, custom_label = labels[wells.index(basic)], labels[wells.index(custom)]
    # the swatches in two group boxes (rounded,
    # the heading underlined in gold — the style of the groups of the program); the labels of Qt (the buddies of the
    # wells, their keys) stay in them, hidden — the heading of the group says it
    from PySide6.QtWidgets import QGroupBox

    for title, label, well in ((tr('Основные цвета'), basic_label, basic),
                               (tr('Пользовательские цвета'), custom_label, custom)):
        group = QGroupBox(title)
        inner = QVBoxLayout(group)
        inner.setContentsMargins(8, 6, 8, 6)
        inner.addWidget(label)
        inner.addWidget(well, 0, Qt.AlignmentFlag.AlignLeft)
        left.addWidget(group)
    left.addSpacing(6)
    manual = QPushButton(tr('Выбрать вручную') + '  ›')
    manual.setCheckable(True)
    manual.setProperty('azimuthNoIcon', True)
    manual.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
    left.addWidget(manual, 0, Qt.AlignmentFlag.AlignLeft)
    # under the swatches, in their column —
    # the part opened by «Выбрать вручную» grows to the right of them and does not move them
    left.addSpacing(14)
    left.addWidget(box)
    left.addStretch(1)
    top.addLayout(left)
    advanced = QGroupBox(tr('Свой цвет'), dialog)
    advanced.setObjectName('colourManual')
    right = QVBoxLayout(advanced)
    right.setContentsMargins(8, 6, 8, 6)
    right.setSpacing(10)
    pick = QHBoxLayout()
    pick.setSpacing(8)
    picker.setMinimumSize(220, 120)
    picker.setMaximumSize(16777215, 16777215)
    picker.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    pick.addWidget(picker, 1)
    strip.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
    strip.setMinimumHeight(120)
    strip.setMaximumHeight(16777215)
    pick.addWidget(strip)
    right.addLayout(pick, 1)
    right.addWidget(shower)
    add.setText(tr('Добавить в набор'))  # to «Пользовательские цвета»
    add.setFixedWidth(add.sizeHint().width())
    # the line «HTML» hidden; in its place, in the grid of the numbers, the pipette and
    # «Добавить в набор»
    from PySide6.QtWidgets import QGridLayout, QLineEdit

    from azimuth.icons import iconify

    iconify(eye, 'pipette', tr('Взять цвет с экрана'))
    html = next((f for f in shower.findChildren(QLineEdit) if f.parentWidget() == shower), None)
    html_label = next((l for l in shower.findChildren(QLabel) if html is not None and l.buddy() == html), None)
    row = QWidget(shower)
    line = QHBoxLayout(row)
    line.setContentsMargins(0, 0, 0, 0)
    line.setSpacing(8)
    line.addWidget(eye)
    for other in rest:  # what Qt shows only while it works (the line of «Взять цвет с экрана»)
        line.addWidget(other)
    line.addStretch(1)
    line.addWidget(add)
    grid = shower.layout()
    if html is not None and isinstance(grid, QGridLayout) and grid.indexOf(html) >= 0:
        at, column, _, _ = grid.getItemPosition(grid.indexOf(html))
        start = column
        if html_label is not None and grid.indexOf(html_label) >= 0:
            start = grid.getItemPosition(grid.indexOf(html_label))[1]
        for widget in (html, html_label):
            if widget is not None:
                widget.hide()
                grid.removeWidget(widget)
        grid.addWidget(row, at, start, 1, max(1, grid.columnCount() - start))
    else:  # another version of Qt: under the numbers
        for widget in (html, html_label):
            if widget is not None:
                widget.hide()
        right.addWidget(row)
    top.addWidget(advanced, 1)
    layout.addLayout(top, 1)  # … the same widgets come back in this one
    for widget in keep + rest:  # a widget put in another layout is hidden by Qt: as it was
        widget.setHidden(hidden.get(widget, False))
    basic_label.hide()
    custom_label.hide()
    # the opened part as tall as the column of
    # the swatches — the field of hues takes what the numbers leave
    advanced.setFixedHeight(max(left.sizeHint().height(), advanced.minimumSizeHint().height()))
    advanced.hide()

    def open_manual(on):
        # the size before the opening is kept and given back when it is closed
        from PySide6.QtCore import QTimer

        manual.setText(tr('Выбрать вручную') + ('  ‹' if on else '  ›'))
        if on:
            dialog._before_manual = dialog.size()
        advanced.setVisible(on)
        dialog.setMinimumSize(0, 0)
        if on:
            dialog.adjustSize()
            return
        before = getattr(dialog, '_before_manual', None)
        dialog.adjustSize()
        if before is not None:
            dialog.resize(before)
            QTimer.singleShot(0, lambda: dialog.resize(before))  # after the layout has given up the room

    manual.toggled.connect(open_manual)
    dialog.manual_button, dialog.manual_part = manual, advanced  # for the tests
    return True


class _Circle(QPushButton):
    def __init__(self, owner):
        super().__init__()
        self.owner = owner
        self.setFixedSize(DOT + 8, DOT + 8)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet('QPushButton { border: none; background: transparent; padding: 0; }')

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        shown = self.owner.shown()
        ring = QColor(self.palette().color(self.foregroundRole()))
        ring.setAlpha(110 if self.underMouse() or self.hasFocus() else 55)
        side = DOT
        circle = QRectF((self.width() - side) / 2, (self.height() - side) / 2, side, side)
        p.setPen(Qt.PenStyle.NoPen)
        if isinstance(shown, tuple):  # a default of two colours (a label: on a coloured atom, on hydrogen) — halves
            p.setBrush(QColor(shown[0]))
            p.drawPie(circle, 90 * 16, 180 * 16)
            p.setBrush(QColor(shown[1]))
            p.drawPie(circle, 270 * 16, 180 * 16)
            p.setBrush(Qt.BrushStyle.NoBrush)
        else:
            p.setBrush(QColor(shown))
        p.setPen(QPen(ring, 1.5))
        p.drawEllipse(circle)
        p.end()


class ColourDot(QWidget):
    """A colour in a circle — pressed, the picker; ↺ beside it puts back the colour of the program (standard())."""

    changed = Signal(str)

    def __init__(self, value, standard, tip, title=None):
        super().__init__()
        self.value, self.standard, self.title = value or '', standard, title or tr('Цвет')
        line = QHBoxLayout(self)
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(2)
        self.circle = _Circle(self)
        self.circle.setToolTip(tr('Выбрать цвет'))
        self.circle.clicked.connect(self.choose)
        self.reset = QToolButton()
        self.reset.setText('↺')
        self.reset.setToolTip(tip)
        self.reset.setAutoRaise(True)
        self.reset.clicked.connect(lambda: self.set(''))
        line.addWidget(self.circle)
        line.addWidget(self.reset)
        self._refresh()

    def shown(self):
        return self.value or self.standard()

    def set(self, value):
        self.value = value or ''
        self._refresh()
        self.changed.emit(self.value)

    def choose(self):
        shown = self.shown()
        colour = pick_colour(shown[0] if isinstance(shown, tuple) else shown, self.window(), self.title)
        if colour:
            self.set(colour)

    def _refresh(self):
        self.reset.setEnabled(bool(self.value))
        self.circle.update()


def font_box(family=''):
    """The fonts of the computer, the first — the one by default ('')."""
    box = QComboBox()
    box.addItem(tr('По умолчанию'), '')
    for name in QFontDatabase.families():
        if not QFontDatabase.isPrivateFamily(name):
            box.addItem(name, name)
    index = box.findData(family or '')
    box.setCurrentIndex(index if index >= 0 else 0)
    box.setMaxVisibleItems(18)
    return box


def family_of(box):
    return box.currentData() or ''


def number(low, high, step, decimals, suffix, value):
    field = QDoubleSpinBox() if decimals else QSpinBox()
    field.setRange(low, high)
    field.setSingleStep(step)
    if decimals:
        field.setDecimals(decimals)
    field.setSuffix(suffix)
    field.setValue(value)
    field.setAlignment(Qt.AlignmentFlag.AlignCenter)
    field.setButtonSymbols(QAbstractSpinBox.ButtonSymbols.UpDownArrows)
    field.setMinimumWidth(150)
    return field


def styled_form(box):
    form = QFormLayout(box)
    form.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
    form.setVerticalSpacing(10)
    form.setHorizontalSpacing(16)
    return form


def row(*widgets, stretch=True):
    """Widgets on one line, on the middle line of each other."""
    holder = QWidget()
    line = QHBoxLayout(holder)
    line.setContentsMargins(0, 0, 0, 0)
    line.setSpacing(10)
    for widget in widgets:
        line.addWidget(widget, 0, Qt.AlignmentFlag.AlignVCenter)
    if stretch:
        line.addStretch(1)
    return holder


def add(form, title, field):
    """A row: its name on the middle line of its field (QFormLayout puts a short name at the top of a tall row)."""
    from PySide6.QtWidgets import QLabel

    if not title:
        form.addRow('', field)
        return field
    name = QLabel(tr(title))
    name.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    name.setMinimumHeight(max(field.sizeHint().height(), name.sizeHint().height()))
    form.addRow(name, field)
    return field
