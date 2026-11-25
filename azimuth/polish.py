"""The finishing touches of every window of the program.

§1 PURPOSE
    The user asked for the same behaviour everywhere, not window by window: the cells of all tables
    centred, and the dialog windows appearing smoothly in the style of the program instead of popping up.
§2 ALGORITHM
    install(app) puts one event filter on the application. It looks only at two kinds of events:
    QEvent.Polish of a QTableView (a table is about to be shown for the first time): the default item delegate is
    replaced by CenterDelegate (every cell centred) and the header gets the centred default alignment; a delegate
    set by the module itself (editors, colours, check boxes) is kept.
    QEvent.Polish of a QPushButton: a button with words gets the icon of its text (give_icon).
    QEvent.Polish of a spin box or a line of text: its value in the middle (center_field); of a combo box — its
    choice in the middle (center_choice, ui.center_combo).
    The program comes back in front (applicationStateChanged → active, came_back): its small windows (owned_windows —
    the settings, the server window…) are raised over the main window; macOS left them behind it (2026-11-23).
    QEvent.Show of a QDialog that is a window (message boxes with Quill, input dialogs, the windows of Compass,
    Sextant and Spectrum): the window fades in (opacity 0 → 1) and slides 10 px down into place, 180 ms, ease-out.
    A window-modal dialog on macOS is a sheet drawn by the system: it is left alone.
§3 APPLICATIONS
    azimuth/app.py main(), hub/launch.py (all the ways the program starts).
§4 SPECIFICATION
    install(app) -> Polisher (kept as a child of app); uninstall(app) -> bool (the tests take it off again);
    CenterDelegate(QStyledItemDelegate); DURATION; SLIDE.
§5 PROCEDURES - below.
§6 NOTES
    No animation under QT_QPA_PLATFORM=offscreen/minimal (tests) and with AZIMUTH_NO_ANIMATION=1.
    The filter returns False for every event but the tooltips: one not wanted (tooltip_wanted) is swallowed, a long
    plain one is shown folded into lines (wrapped_tip — Qt draws a plain tooltip as one line, on Windows as wide as the
    screen).
§7 TESTS
    tests/core/test_polish.py (the decision functions without a display).
§8' ROBUSTNESS
    Any error inside the filter is caught: a finishing touch never breaks a window.
"""

import os
import sys

from PySide6.QtCore import (QAbstractAnimation, QEasingCurve, QEvent, QObject, QParallelAnimationGroup, QPoint,
                            QPropertyAnimation, Qt)
from PySide6.QtWidgets import (QAbstractSpinBox, QComboBox, QDialog, QFileDialog, QLineEdit, QMenu, QPushButton,
                               QStyledItemDelegate, QTableView, QWidget)

DURATION = 180  # ms
SLIDE = 10  # px


def animations_allowed(environ=None, platform_name=''):
    """False in the tests (offscreen/minimal platforms) and when switched off by AZIMUTH_NO_ANIMATION=1."""
    environ = os.environ if environ is None else environ
    if environ.get('AZIMUTH_NO_ANIMATION') == '1':
        return False
    platform_name = platform_name or environ.get('QT_QPA_PLATFORM', '')
    return platform_name not in ('offscreen', 'minimal')


def is_sheet(modality, platform=None):
    """A window-modal dialog on macOS is shown by the system as a sheet; it must not be moved or faded."""
    return (platform or sys.platform) == 'darwin' and modality == Qt.WindowModality.WindowModal


class CenterDelegate(QStyledItemDelegate):
    """The default delegate, with the text of every cell centred."""

    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        option.displayAlignment = Qt.AlignmentFlag.AlignCenter


# -- fewer tooltips ------------------------------------------------------------------------------------------
# Fewer tooltips: those repeating the words shown and those of frames, lists and empty places go; those of icons without
# words, of fields that explain a
# setting and of cut text stay. A tooltip is shown by the widget under the pointer itself (otherwise Qt passes the
# event up and a container's tooltip shows over every empty place of it).

def _plain(text):
    import re

    return re.sub(r'<[^>]+>', '', text or '').replace('&', '').replace('…', '').replace('...', '').strip().lower()


def _repeats(tip, shown):
    """The tooltip says no more than the words shown (the same, or the same words first and little more)."""
    tip, shown = _plain(tip), _plain(shown)
    return bool(shown) and (tip == shown or (tip.startswith(shown) and len(tip) <= len(shown) + 3))


TIP_LINE = 80  # characters: a plain tooltip longer than this is folded into lines


def wrapped_tip(text):
    """A long plain tooltip as rich text, which Qt folds into lines; None for a short one or one already rich. A plain
    tooltip is one line of any length — on Windows across the whole screen (the owner's laptop, 2026-11-24: the tip of
    «Окружение для» of the server window)."""
    import html
    import re

    if not text or len(text) <= TIP_LINE or re.search(r'<[a-zA-Z/!][^>]*>', text):
        return None
    return '<p>' + html.escape(text).replace('\n', '<br>') + '</p>'


def tooltip_wanted(obj, event, under=None):
    """Whether the tooltip asked of obj (a QHelpEvent) is shown (see above)."""
    from PySide6.QtWidgets import (QAbstractButton, QAbstractItemView, QAbstractSlider, QAbstractSpinBox,
                                   QApplication, QComboBox, QDialog, QFrame, QGroupBox, QLabel, QLineEdit, QMainWindow,
                                   QPlainTextEdit, QScrollArea, QSplitter, QStackedWidget, QTabBar, QTabWidget,
                                   QTextEdit, QWidget)

    if not isinstance(obj, QWidget):
        return True
    view = obj.parent() if obj.parent() is not None and isinstance(obj.parent(), QAbstractItemView) else None
    if view is not None and obj is view.viewport():  # a cell: its tooltip unless it repeats a cell that shows it whole
        index = view.indexAt(event.pos())
        if not index.isValid():
            return False  # below the rows: an empty place (the tooltip of the list is not shown there either)
        tip = index.data(Qt.ItemDataRole.ToolTipRole)
        shown = index.data(Qt.ItemDataRole.DisplayRole)
        if tip and shown is not None and _repeats(str(tip), str(shown)):
            width = view.fontMetrics().horizontalAdvance(str(shown)) + 12
            return width > view.visualRect(index).width()  # cut — the whole of it is said
        return True
    if not obj.toolTip() or isinstance(obj, QTabBar):
        return True  # nothing of its own (Qt asks the parents next — they are checked then); a tab says its own
    under = under if under is not None else QApplication.widgetAt(event.globalPos())
    near = under is obj or (under is not None and obj.isAncestorOf(under) and (
        isinstance(obj, (QAbstractSpinBox, QComboBox, QAbstractButton)) or under.focusProxy() is obj))
    if not near:
        return False  # the tooltip of a parent over a place of a child without one: an «empty place»
    if type(obj) is QWidget or isinstance(obj, (QMainWindow, QDialog, QGroupBox, QStackedWidget, QTabWidget,
                                                QScrollArea, QSplitter)) or (
            isinstance(obj, QFrame) and not isinstance(obj, QLabel) and type(obj).__name__ in ('QFrame',)):
        return False  # a frame, a page, a window
    controls = (QAbstractButton, QAbstractSpinBox, QComboBox, QLineEdit, QAbstractSlider, QLabel, QAbstractItemView,
                QTextEdit, QPlainTextEdit)
    if not isinstance(obj, controls) and obj.layout() is not None and obj.layout().count():
        return False  # a panel of its own kind holding other widgets: its empty places say nothing
    # an icon button that unfolds its words only on hover (ExpandingButton, azimuth.controls) keeps its tooltip:
    # the words are not shown
    shown = obj.text() if isinstance(obj, QAbstractButton) else ''
    if isinstance(obj, QAbstractButton) and obj.property('expanding') and not getattr(obj, 'unfolded', False):
        shown = ''
    if shown and _repeats(obj.toolTip(), shown):
        return False
    if isinstance(obj, QLabel):
        return not _repeats(obj.toolTip(), obj.text())
    return True


def center_field(field):
    """The value of a field in its middle — the spin boxes and the lines of text; not the line of a file
    window (a path), not a field that asks to stay as it is (azimuthKeepAlignment). True when it was centred."""
    if field.property('azimuthKeepAlignment'):
        return False
    parent = field.parentWidget()
    while parent is not None:
        if isinstance(parent, QFileDialog):
            return False
        parent = parent.parentWidget()
    if isinstance(field, QLineEdit) and isinstance(field.parentWidget(), QAbstractSpinBox):
        return False  # the line of a spin box: the spin box sets it
    field.setAlignment(Qt.AlignmentFlag.AlignCenter)
    return True


def center_choice(combo):
    """The choice of a combo box in its middle, as the values of the spin boxes (the owner, 2026-11-23: «центрируй в
    полях все» — the lists of «Настройки» stood at the left, the numbers in the middle); not an editable one, not one
    of a file window, not one that asks to stay as it is (azimuthKeepAlignment). True when it was centred."""
    if combo.isEditable() or combo.property('azimuthKeepAlignment'):
        return False
    parent = combo.parentWidget()
    while parent is not None:
        if isinstance(parent, QFileDialog):
            return False
        parent = parent.parentWidget()
    from azimuth.ui import center_combo

    center_combo(combo)
    return True


# the filter of the whole application sees
# every event of every widget — a sliding panel moves and repaints hundreds of them a frame; the ones it does not want
# leave at the first test (one look-up in a set) instead of a row of comparisons and isinstance checks
WANTED = frozenset((QEvent.Type.Polish, QEvent.Type.Show, QEvent.Type.ToolTip))


NO_COLON = (':', '?', '…', '.', '!', '：')


def _form_of(widget):
    """The QFormLayout of a widget shown, or None (anything else — a QWindow, a widget without one)."""
    from PySide6.QtWidgets import QFormLayout, QWidget

    if not isinstance(widget, QWidget):
        return None
    layout = widget.layout()
    return layout if isinstance(layout, QFormLayout) else None


def colon_labels(widget):
    """The name of a row of a form (QFormLayout, the column of names) ends with a colon — added when the row is shown,
    after the translation (the texts of the program and of tr() stay without it). A name that ends with a sign already,
    rich text and an empty one stay. Returns the labels changed."""
    from PySide6.QtWidgets import QFormLayout, QLabel

    changed = []
    forms = list(widget.findChildren(QFormLayout))
    if isinstance(getattr(widget, 'layout', lambda: None)(), QFormLayout):
        forms.append(widget.layout())
    for form in forms:
        for row in range(form.rowCount()):
            item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
            label = item.widget() if item is not None else None
            if not isinstance(label, QLabel):
                continue
            text = label.text()
            plain = text.rstrip()
            if not plain or plain.startswith('<') or plain.endswith(NO_COLON):
                continue
            label.setText(plain + ':')
            changed.append(label)
    return changed


OK_TEXTS = ('OK', 'ОК', 'Ок', 'Ok')  # the Latin and the Cyrillic spelling


def blue_ok(dialog):
    """«OK» of a window is its main
    action — blue (#primary, the rule of the buttons of 2026-11-17), whether it is the OK of a QDialogButtonBox or a
    button of its own called so. A window that has another blue button (its own main action) keeps it, OK too.
    Returns the buttons made blue."""
    from PySide6.QtWidgets import QDialogButtonBox

    made = []
    for box in dialog.findChildren(QDialogButtonBox):
        button = box.button(QDialogButtonBox.StandardButton.Ok)
        if button is not None:
            made.append(button)
    for button in dialog.findChildren(QPushButton):
        if button not in made and button.text().replace('&', '').strip() in OK_TEXTS:
            made.append(button)
    made = [b for b in made if b.objectName() != 'primary']
    for button in made:
        button.setObjectName('primary')
        button.style().unpolish(button)
        button.style().polish(button)
    return made


class Polisher(QObject):
    def came_back(self, state):
        """The program is in front again (the user came back from another one): its small windows over the main window.
        macOS brought only the window clicked forward, and the settings, the server window and the like stayed behind
        the main window — looked for, or opened a second time (the owner, 2026-11-23)."""
        if state != Qt.ApplicationState.ApplicationActive:
            return
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        def lift():
            try:
                for widget in owned_windows(QApplication.topLevelWidgets()):
                    widget.raise_()  # raised, not activated: the keyboard stays where the user clicked
            except Exception:  # noqa: BLE001 — a finishing touch never breaks a window
                pass

        QTimer.singleShot(0, lift)  # after the system has put the window clicked in front

    def __init__(self, app):
        super().__init__(app)
        self.animate = animations_allowed(platform_name=app.platformName() if hasattr(app, 'platformName') else '')
        self._running = {}

    def eventFilter(self, obj, event):
        kind = event.type()
        if kind not in WANTED:
            return False
        try:
            if kind == QEvent.Type.Polish and isinstance(obj, QTableView):
                self.center(obj)
            elif kind == QEvent.Type.Polish and isinstance(obj, QPushButton):
                self.give_icon(obj)
            elif kind == QEvent.Type.Polish and isinstance(obj, (QAbstractSpinBox, QLineEdit)):
                center_field(obj)
            elif kind == QEvent.Type.Polish and isinstance(obj, QComboBox):
                center_choice(obj)
            elif kind == QEvent.Type.Show and isinstance(obj, QMenu):
                self.give_menu_icons(obj)
            elif kind == QEvent.Type.Show and isinstance(obj, QDialog) and obj.isWindow():
                blue_ok(obj)
                colon_labels(obj)
                if self.animate:
                    self.appear(obj)
            elif kind == QEvent.Type.Show and _form_of(obj) is not None:  # a form of a panel shown
                colon_labels(obj)
            elif kind == QEvent.Type.ToolTip and not tooltip_wanted(obj, event):
                from PySide6.QtWidgets import QToolTip

                QToolTip.hideText()
                event.ignore()
                return True  # a tooltip that is not wanted (§2)
            elif kind == QEvent.Type.ToolTip and isinstance(obj, QWidget) and wrapped_tip(obj.toolTip()):
                from PySide6.QtWidgets import QToolTip

                QToolTip.showText(event.globalPos(), wrapped_tip(obj.toolTip()), obj)
                return True  # shown here, folded into lines (wrapped_tip)
        except Exception:  # noqa: BLE001 — §8'
            pass
        return False

    @staticmethod
    def give_icon(button):
        """A text button gets the glyph of its text (azimuth/button_icons.py) — not the icon-only ones, the
        ones with an icon, the checkable segments, the navigation, a button asking none (azimuthNoIcon)."""
        if (button.property('azimuthIconChecked') or button.property('iconic') or button.property('azimuthNoIcon')
                or not button.icon().isNull() or button.isCheckable() or button.objectName() == 'nav'):
            return
        button.setProperty('azimuthIconChecked', True)
        from azimuth.button_icons import icon_name

        name = icon_name(button.text())
        if name is None:
            return
        from PySide6.QtCore import QSize

        from azimuth.icons import icon

        button.setIcon(icon(name, '#ffffff' if button.objectName() == 'primary' else None))
        button.setIconSize(QSize(16, 16))
        button.setProperty('azimuthTextIcon', name)

    @staticmethod
    def give_menu_icons(menu):
        """The items of a menu get the glyphs of their texts (menus are filled just before they show)."""
        from azimuth.button_icons import icon_name
        from azimuth.icons import icon

        for action in menu.actions():
            if (action.isSeparator() or action.isCheckable() or action.menu() is not None
                    or not action.icon().isNull() or action.property('azimuthNoIcon')):
                continue
            name = icon_name(action.text())
            if name is not None:
                action.setIcon(icon(name))
                action.setProperty('azimuthTextIcon', name)

    @staticmethod
    def center(view):
        if view.property('azimuthCentred'):
            return
        view.setProperty('azimuthCentred', True)
        if type(view.itemDelegate()) is QStyledItemDelegate:  # the default one: a module's own delegate stays
            view.setItemDelegate(CenterDelegate(view))
        for header in (view.horizontalHeader(), view.verticalHeader()):
            if header is not None:
                header.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)

    def appear(self, dialog):
        if (is_sheet(dialog.windowModality()) or dialog.property('azimuthNoFade') or id(dialog) in self._running
                or dialog.testAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)):  # a native file or colour dialog
            return
        # the place the dialog slides to is
        # the middle of its window (azimuth.ui.centre_first) — it was read before the centring, and the slide took the
        # dialog back to the corner
        from azimuth.ui import centre_first

        centre_first(dialog)
        end = dialog.pos()
        dialog.setProperty('azimuthSliding', True)
        group = QParallelAnimationGroup(dialog)
        fade = QPropertyAnimation(dialog, b'windowOpacity', group)
        fade.setStartValue(0.0)
        fade.setEndValue(1.0)
        slide = QPropertyAnimation(dialog, b'pos', group)
        slide.setStartValue(end - QPoint(0, SLIDE))
        slide.setEndValue(end)
        for animation in (fade, slide):
            animation.setDuration(DURATION)
            animation.setEasingCurve(QEasingCurve.Type.OutCubic)
            group.addAnimation(animation)
        key = id(dialog)
        self._running[key] = group

        def done():
            self._running.pop(key, None)
            dialog.setWindowOpacity(1.0)
            dialog.setProperty('azimuthSliding', False)

        group.finished.connect(done)
        dialog.setWindowOpacity(0.0)
        group.start(QAbstractAnimation.DeletionPolicy.DeleteWhenStopped)


def install(app):
    """One filter for the whole application (§2). Calling it twice installs it once."""
    for child in app.children():
        if isinstance(child, Polisher):
            return child
    polisher = Polisher(app)
    app.installEventFilter(polisher)
    app.applicationStateChanged.connect(polisher.came_back)
    return polisher


def owned_windows(windows):
    """The small windows of the program to keep over its main window: shown, not minimized, windows of their own with an
    owner (settings, «Сервер для расчётов», a calculation in its window) — not the main window (it has no owner), menus,
    tooltips or popups."""
    found = []
    for widget in windows:
        try:
            if not (widget.isWindow() and widget.isVisible() and not widget.isMinimized()):
                continue
            if widget.parentWidget() is None or isinstance(widget, QMenu):
                continue
            if widget.windowType() in (Qt.WindowType.Popup, Qt.WindowType.ToolTip, Qt.WindowType.SplashScreen):
                continue
        except RuntimeError:  # deleted meanwhile
            continue
        found.append(widget)
    return found


def uninstall(app):
    """The filter taken off the application (True if there was one). The tests that install it take it off again: left
    on, it watched every event of the next test files too, and the language switch of the Atlas (tests/hub/test_hub.py,
    after test_gui.py) ended in a segmentation fault — the full run only, the file alone passed."""
    found = False
    for child in list(app.children()):
        if isinstance(child, Polisher):
            app.removeEventFilter(child)
            child.setParent(None)
            child.deleteLater()
            found = True
    return found
