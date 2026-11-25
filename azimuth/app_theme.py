"""The theme of Azimuth applied to the window: the light and dark sheets, following the theme of the system, the
look of the combo boxes made after the start. Methods of Studio (self is the window), kept here to make app.py
shorter; the colours themselves are azimuth/theme.py.

Split off azimuth/app.py (0.222.30).
"""

from PySide6.QtCore import Qt
from PySide6.QtGui import QPalette, QColor
from PySide6.QtWidgets import QApplication, QComboBox, QTableWidget, QListView
from .icons import iconify
from .ui import smooth
from azimuth.i18n import tr
from azimuth.ui import center_combo, combo_row_delegate, wide_popup
from azimuth.app_style import theme_style_sheet


def system_prefers_dark():
    """True when the operating system uses a dark appearance (Qt 6.5+ colour scheme; else the palette)."""
    app = QApplication.instance()
    try:
        scheme = app.styleHints().colorScheme()
        if scheme == Qt.ColorScheme.Dark:
            return True
        if scheme == Qt.ColorScheme.Light:
            return False
    except AttributeError:
        pass
    # no colour scheme (Qt < 6.5): the style's own palette, not the one the program set for its theme
    return app.style().standardPalette().window().color().lightness() < 128


def install_combo_theme(self):
    """The combo boxes made after the start (the windows opened later: CUBE, the crystal, the reaction diagram…) get
    the look of the theme. Without a filter of the whole application — the mere presence of one written in Python
    (even an empty one) crashed Qt in the tests of the hub, which make and delete windows while the Atlas loads
    (segmentation fault on; the versions and an empty filter were run one by one on the user's Mac). Now the window
    watches only its own children: a window made with it as its parent (a dialog) or a part of it restyles its new
    combo boxes when it is shown (style_new_combos); navigate does the same."""
    if getattr(self, '_combo_filter', None) is not None:
        return self._combo_filter
    from PySide6.QtCore import QEvent, QObject

    owner = self

    class ShownTheme(QObject):
        def eventFilter(self, obj, event):
            try:
                kind = event.type()
                if kind == QEvent.Type.ChildAdded and obj is owner:
                    child = event.child()
                    if child is not None and child.isWidgetType():
                        child.installEventFilter(self)
                elif kind == QEvent.Type.Show and obj is not owner:
                    owner.style_new_combos(obj)
            except (RuntimeError, AttributeError):  # a window being deleted
                pass
            return False

    self._combo_filter = ShownTheme(self)
    self.installEventFilter(self._combo_filter)
    for child in self.children():
        if child.isWidgetType():
            child.installEventFilter(self._combo_filter)
    return self._combo_filter


def style_new_combos(self, root):
    """The combo boxes under root not yet in the look of the theme get it; returns how many."""
    theme = getattr(self, '_combo_theme', None)
    if theme is None or root is None:
        return 0
    combos = root.findChildren(QComboBox)
    if isinstance(root, QComboBox):
        combos.append(root)
    fresh = [c for c in combos if c.property('quail_theme') != theme[1]]
    for combo in fresh:
        self.style_combo(combo)
    return len(fresh)


def style_combo(self, combo):
    """The combo box in the style of the program: centred text, the list of the theme, rounded, as wide as its items."""
    palette, dark, background, foreground, border = self._combo_theme
    combo.setProperty('quail_theme', dark)
    center_combo(combo)
    if not combo.property('quail_list'):
        combo.setView(QListView(combo))
        combo.view().setItemDelegate(combo_row_delegate(combo.view()))  # rows of their full height
        combo.setProperty('quail_list', True)
    view = combo.view()
    combo.setPalette(palette)
    view.setPalette(palette)
    view.viewport().setPalette(palette)
    pick = '#26364f' if dark else '#e4ecf8'
    view.setStyleSheet(
        f"QAbstractItemView {{background: {background}; color: {foreground}; border: 1px solid {border}; border-radius: 9px; padding: 4px; selection-background-color: {pick}; selection-color: {foreground}; outline: none;}} QAbstractItemView::item {{padding: 6px 10px; min-height: 20px; border-radius: 6px;}} QAbstractItemView::item:hover, QAbstractItemView::item:selected {{background: {pick}; color: {foreground};}} QAbstractItemView > QWidget {{background: transparent;}}"
    )
    popup = view.window()
    if popup is not combo.window() and not popup.property('quail_round'):
        popup.setWindowFlags(
            popup.windowFlags() | Qt.WindowType.FramelessWindowHint | Qt.WindowType.NoDropShadowWindowHint
        )
        popup.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        popup.setProperty('quail_round', True)
        popup.setStyleSheet('background: transparent; border: none;')
        smooth(popup)
    view.viewport().setAutoFillBackground(
        False
    )  # the square viewport drew corners over the rounded list
    view.window().setPalette(palette)
    wide_popup(combo)


def follows_system_theme(self):
    return str(self.preferences.value(self.THEME_FOLLOWS_SYSTEM, 'false')).lower() in ('true', '1')


def set_theme_follows_system(self, on):
    """The theme of the system now and whenever it changes, until a theme is chosen by hand."""
    self.preferences.setValue(self.THEME_FOLLOWS_SYSTEM, bool(on))
    self.preferences.sync()
    if on:
        self.system_theme_changed()


def system_theme_changed(self):
    """The system's appearance changed (or «Как в системе» was chosen): the theme follows it."""
    if not self.follows_system_theme():
        return False
    target = 1 if system_prefers_dark() else 0
    if self.theme.currentIndex() != target:
        self.theme.setCurrentIndex(target)
    return True


def apply_theme(self, *args):
    # no painting until everything is restyled (each intermediate repaint of the window cost time)
    top = self.window()
    top.setUpdatesEnabled(False)
    try:
        self._apply_theme()
    finally:
        top.setUpdatesEnabled(True)


def _apply_theme(self):
    dark = self.theme.currentIndex() == 1
    # Fully specify both themes: the OS palette may itself be dark.
    palette = QPalette()
    colors = {
        'Window': ('#f5f6f8', '#191f28'),
        'Base': ('#fbfcfd', '#11151c'),
        'AlternateBase': ('#edf2f5', '#212833'),
        'Text': ('#1b2230', '#e7eaf0'),
        'WindowText': ('#1b2230', '#e7eaf0'),
        'Button': ('#f8fafc', '#212833'),
        'ButtonText': ('#1b2230', '#e7eaf0'),
        'Highlight': ('#2a62b8', '#2a62b8'),
        'HighlightedText': ('#ffffff', '#ffffff'),
        'ToolTipBase': ('#fbfcfd', '#212833'),
        'ToolTipText': ('#1b2230', '#e7eaf0'),
        'PlaceholderText': ('#5b6474', '#9aa3b2'),
    }
    for role, pair in colors.items():
        palette.setColor(getattr(QPalette.ColorRole, role), QColor(pair[int(dark)]))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        palette.setColor(QPalette.ColorGroup.Disabled, role, QColor('#80909d' if dark else '#657b89'))
    self.setPalette(palette)
    background = '#11151c' if dark else '#fbfcfd'
    foreground = '#e7eaf0' if dark else '#1b2230'
    border = '#2b333f' if dark else '#d8dce3'
    from azimuth import theme_sheet

    application = QApplication.instance()
    application.setPalette(palette)
    # one sheet holds both
    # themes, set once (≈1.2 s, at the start); the theme is the property of the windows (theme_sheet.mark, ≈0.2 s)
    sheet = theme_style_sheet()
    if application.styleSheet() != sheet:
        application.setStyleSheet(sheet)
    theme_sheet.mark(application, dark)
    theme_sheet.watch(application)
    # the same style sheet was also set on this window — every widget was styled twice; the one of the
    # application covers it
    if self.styleSheet():
        self.setStyleSheet('')
    # Use ordinary list delegates rather than platform menu delegates.

    # the look of the combo boxes is kept for the ones made later too (the windows opened after the start:
    # CUBE, the crystal, the reaction diagram…) — style_combo when a combo box is first polished (ComboTheme)
    self._combo_theme = (palette, dark, background, foreground, border)
    self.install_combo_theme()
    for combo in self.findChildren(QComboBox):
        self.style_combo(combo)
    for table in self.findChildren(QTableWidget):
        table.setPalette(palette)
        table.viewport().setPalette(palette)
        table.horizontalHeader().setPalette(palette)
        table.verticalHeader().setPalette(palette)
    iconify(self.theme_toggle, 'sun' if dark else 'moon', tr('Светлая тема') if dark else tr('Тёмная тема'))
    self.viewer.dark = dark
    self.viewer.update()
    if hasattr(self, 'update_side_quill'):
        self.update_side_quill()  # the bubble of Quill in the colours of the theme
    if hasattr(self, 'next_button'):  # the arrow button paints itself in the colour of the theme
        self.next_button.dark = dark
        self.next_button.update()
    for item in getattr(self, 'where_buttons', {}).values():  # so do «Этот компьютер» / «Сервер»
        item.dark = dark
        item.update()
    self.drawer.plot.update()
    self.vibrations.viewer.dark = dark
    self.vibrations.viewer.update()
    self.vibrations.spectrum.update()
    if self.cube_dialog is not None:
        self.cube_dialog.set_theme(dark)
    self.preferences.setValue('theme', 'dark' if dark else 'light')
    self.preferences.sync()  # written at once — kept even when the program is not closed normally
