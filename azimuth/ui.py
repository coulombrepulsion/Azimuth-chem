"""Shared Qt widget helpers, retaining the existing interface."""

from pathlib import Path

from PySide6.QtCore import QStandardPaths
from PySide6.QtWidgets import QFileDialog, QLabel, QPushButton, QFrame, QVBoxLayout
from azimuth.ui_windows import help_button, _HelpPopup, show_help, StatusEcho, freeze_ornaments, DialogCentre, centre_first, fit_pill, copied  # noqa: F401 — also named from here


def label(text, name=None):
    item = QLabel(text)
    item.setWordWrap(True)
    if name:
        item.setObjectName(name)
    return item


def button(text, callback, primary=False):
    item = QPushButton(text)
    if primary:
        item.setObjectName('primary')
    item.clicked.connect(callback)
    return item


def card(title):
    frame = QFrame()
    frame.setObjectName('card')
    layout = QVBoxLayout(frame)
    layout.setContentsMargins(22, 20, 22, 20)
    layout.setSpacing(13)
    layout.addWidget(label(title, 'cardtitle'))
    return frame, layout


class Spinner(QFrame):
    """The sign of waiting by the pill of Compass and in the status bar (run_waiting, «Esc — отменить»);
    the compass of the icon, as azimuth.controls.Spinner, its needle swinging
    (controls.swing) by the clock; the light or dark colours of the icon after the text it stands by."""

    SIZE = 20
    TURN_MS = 900  # kept for the callers that read it: about one turn

    WIDE = 34  # the spectrum: wider than high

    def __init__(self, parent=None, colour=None, kind='compass'):
        """kind: 'compass', 'sextant' (the
        sextant of hub.job_indicator, its arm moving) or 'spectrum' (the recorded spectrum of spectrum_pulse)."""
        super().__init__(parent)
        from PySide6.QtCore import QElapsedTimer, QTimer, Qt

        self.colour = colour
        self.kind = kind
        self.setFixedSize(self.WIDE if kind == 'spectrum' else self.SIZE, self.SIZE)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setStyleSheet('background: transparent; border: none;')
        self.clock = QElapsedTimer()
        self.clock.start()
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.update)
        self.timer.start()

    def ink(self):
        from PySide6.QtGui import QColor, QPalette

        if self.colour is not None:
            return QColor(self.colour)
        host = self.parentWidget() or self
        return host.palette().color(QPalette.ColorRole.WindowText)

    def angle(self):
        from azimuth.controls import swing

        return swing(self.clock.elapsed() / 1000.0)

    def paintEvent(self, event):
        from PySide6.QtGui import QPainter

        from azimuth.controls import draw_compass

        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # a light text stands on a dark ground: the colours of the dark icon
        ink = self.ink()
        dark = ink.lightness() > 128
        seconds = self.clock.elapsed() / 1000.0
        if self.kind == 'sextant':
            from hub.job_indicator import draw_sextant

            draw_sextant(p, self.height(), seconds, dark)
        elif self.kind == 'spectrum':
            from PySide6.QtCore import QRectF
            from PySide6.QtGui import QColor

            from modules.spectrum.views.spectrum_pulse import draw_pulse

            axis = QColor(ink)
            axis.setAlpha(120)
            draw_pulse(p, QRectF(self.rect()).adjusted(1, 2, -1, -2), seconds, dark, axis)
        else:
            draw_compass(p, self.width(), self.height(), self.angle(), dark)
        p.end()


class ElideLabel(QLabel):
    """One line that ends in «…» when the text does not fit (the full text is in the tooltip)."""

    def __init__(self, text='', name=None):
        super().__init__()
        self.full = ''
        if name:
            self.setObjectName(name)
        from PySide6.QtWidgets import QSizePolicy

        self.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Preferred)
        self.setText(text)

    def setText(self, text):
        self.full = text or ''
        self.setToolTip(self.full)
        self._elide()

    def text(self):
        return self.full

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._elide()

    def _elide(self):
        from PySide6.QtCore import Qt

        QLabel.setText(
            self, self.fontMetrics().elidedText(self.full, Qt.TextElideMode.ElideRight, max(10, self.width()))
        )


class _PopupFade:
    """Popups (menus, lists of combo boxes) fade in over 140 ms instead of appearing at once.
    They also slide down a few pixels as they open, and menus fold back the same way when they close
    (a picture of the menu fades and rises; the menu itself is already gone, nothing waits for it)."""

    filter = None
    ghosts = []  # the pictures of closing menus (top-level, kept alive here until their animation ends)
    SHIFT = 8  # px the popup travels
    OPEN_MS, CLOSE_MS = 160, 140

    @classmethod
    def get(cls):
        if cls.filter is None:
            from PySide6.QtCore import QEasingCurve, QEvent, QObject, QParallelAnimationGroup, QPoint, QPropertyAnimation

            class Fade(QObject):
                def eventFilter(self, watched, event):
                    if event.type() == QEvent.Type.Show and watched.isWindow():
                        system_corners_off(watched)
                        group = QParallelAnimationGroup(watched)
                        anim = QPropertyAnimation(watched, b'windowOpacity', group)
                        anim.setDuration(cls.OPEN_MS)
                        anim.setStartValue(0.0)
                        anim.setEndValue(1.0)
                        anim.setEasingCurve(QEasingCurve.Type.OutCubic)
                        group.addAnimation(anim)
                        end = watched.pos()
                        move = QPropertyAnimation(watched, b'pos', group)
                        move.setDuration(cls.OPEN_MS)
                        move.setStartValue(end - QPoint(0, cls.SHIFT))
                        move.setEndValue(end)
                        move.setEasingCurve(QEasingCurve.Type.OutCubic)
                        group.addAnimation(move)
                        watched.setWindowOpacity(0.0)
                        group.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)
                    return False

            cls.filter = Fade()
            # the system animations of menus and lists off — on Windows they ran first and then ours, so a
            # menu showed twice (a jerk at the start); ours is the only one now
            from PySide6.QtCore import Qt
            from PySide6.QtWidgets import QApplication

            for effect in (Qt.UIEffect.UI_AnimateMenu, Qt.UIEffect.UI_FadeMenu, Qt.UIEffect.UI_AnimateCombo):
                QApplication.setEffectEnabled(effect, False)
        return cls.filter

    @classmethod
    def fold(cls, menu):
        """A menu about to close: its picture fades out while rising SHIFT px."""
        from PySide6.QtCore import QEasingCurve, QParallelAnimationGroup, QPoint, QPropertyAnimation, Qt
        from PySide6.QtWidgets import QLabel

        if not menu.isVisible() or menu.width() <= 0:
            return
        ghost = QLabel(None, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        ghost.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        ghost.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        ghost.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        ghost.setPixmap(menu.grab())
        ghost.setGeometry(menu.geometry())
        ghost.show()
        group = QParallelAnimationGroup(ghost)
        fade = QPropertyAnimation(ghost, b'windowOpacity', group)
        fade.setDuration(cls.CLOSE_MS)
        fade.setStartValue(1.0)
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InCubic)
        rise = QPropertyAnimation(ghost, b'pos', group)
        rise.setDuration(cls.CLOSE_MS)
        rise.setStartValue(menu.pos())
        rise.setEndValue(menu.pos() - QPoint(0, cls.SHIFT))
        rise.setEasingCurve(QEasingCurve.Type.InCubic)
        group.addAnimation(fade)
        group.addAnimation(rise)
        cls.ghosts.append(ghost)

        def done(ghost=ghost):
            ghost.hide()
            if ghost in cls.ghosts:
                cls.ghosts.remove(ghost)
            ghost.deleteLater()

        group.finished.connect(done)
        group.start()


def open_window(box):
    """a window of settings opened as a window of its own — with its title bar and name, as the picker of colours — not
    as a sheet of macOS (QDialog.open makes a window-modal dialog, which macOS shows as a sheet without a title). It
    still holds the program until it is closed (application-modal) and does not wait (as open). Returns the window."""
    from PySide6.QtCore import Qt

    box.setWindowModality(Qt.WindowModality.ApplicationModal)
    box.show()
    box.raise_()
    box.activateWindow()
    return box


DWMWA_WINDOW_CORNER_PREFERENCE, DWMWCP_DONOTROUND = 33, 1  # dwmapi.h (Windows 11)


def system_corners_off(popup):
    """Windows 11 rounds a popup window itself (DWM, its own radius of about 8 px) over the corners the style sheet
    draws (9 px) — the corners of menus and lists came out uneven or cut (the owner's Windows, 2026-11-28: «Края
    обрезаны неровно или вообще не обрезаны»). A popup drawn translucent with its own corners (rounded,
    app_theme.style_combo — the property quail_round) asks DWM not to round it. Elsewhere, on Windows 10 (the
    attribute is unknown there) and for other windows — nothing. True when asked."""
    import sys

    if sys.platform != 'win32' or popup is None or not popup.property('quail_round'):
        return False
    try:
        import ctypes

        value = ctypes.c_int(DWMWCP_DONOTROUND)
        result = ctypes.windll.dwmapi.DwmSetWindowAttribute(ctypes.c_void_p(int(popup.winId())),
                                                            DWMWA_WINDOW_CORNER_PREFERENCE, ctypes.byref(value),
                                                            ctypes.sizeof(value))
    except (OSError, AttributeError, ValueError, TypeError):
        return False
    return result == 0


class _MenuRounding:
    """Every menu of the application drawn with the rounded corners of the style sheet — the menus of the menu bar of
    Windows and Linux, the context menus of text fields (createStandardContextMenu) and the submenus too, not only
    those passed to rounded(): they were square windows behind a border of 9 px, and their corners showed the
    background (the owner's Windows, 2026-11-28; the same on the Mac). A menu is made translucent when it is polished — QMenu.popup polishes
    it before its window is created, the only moment its flags can change without a new window."""

    filter = None

    @classmethod
    def install(cls, app):
        from PySide6.QtCore import QEvent, QObject, Qt
        from PySide6.QtWidgets import QMenu

        # the Mac too (0.249.32): the menus of the program are drawn by Qt there as well (the menu bar of the window is
        # not native: setNativeMenuBar(False)), and the square window showed behind the corners of «Поля…»
        if app is None or cls.filter is not None:
            return False

        class Rounding(QObject):
            def eventFilter(self, watched, event):
                if (event.type() == QEvent.Type.Polish and isinstance(watched, QMenu)
                        and not watched.property('quail_round')
                        and not watched.testAttribute(Qt.WidgetAttribute.WA_WState_Created)):
                    rounded(watched)
                return False

        cls.filter = Rounding(app)
        app.installEventFilter(cls.filter)
        return True


def round_menus(app):
    """All the menus of the application rounded (_MenuRounding); once — True when installed now."""
    return _MenuRounding.install(app)


def rounded(menu):
    """A menu drawn with the rounded corners of the style sheet — no square window behind them (of
    modules/sextant/job_window.py; also for menus made in code, not only those of the menu bar); it fades in as the
    others (smooth). Returns the menu."""
    from PySide6.QtCore import Qt

    if menu is not None and not menu.property('quail_round'):
        menu.setProperty('quail_round', True)  # first: the flags below are set once (_MenuRounding asks while polishing)
        menu.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        menu.setWindowFlags(menu.windowFlags() | Qt.WindowType.FramelessWindowHint
                            | Qt.WindowType.NoDropShadowWindowHint)
    return smooth(menu)


def smooth(widget):
    """Let a popup (QMenu, a combo box's list window) fade in; returns the widget."""
    if widget is not None and not widget.property('quail_fade'):
        widget.installEventFilter(_PopupFade.get())
        widget.setProperty('quail_fade', True)
        from PySide6.QtWidgets import QMenu

        if isinstance(widget, QMenu):  # and folds back when it closes
            widget.aboutToHide.connect(lambda menu=widget: _PopupFade.fold(menu))
            # transparent before it is shown — on Windows the first frame came at full opacity, before the fade
            widget.aboutToShow.connect(lambda menu=widget: menu.setWindowOpacity(0.0))
    return widget


class _CenteredCombo:
    """The current item of a combo box is drawn in the middle of the field (the list still opens below)."""

    filter = None

    @classmethod
    def get(cls):
        if cls.filter is None:
            from PySide6.QtCore import QEvent, QObject, Qt
            from PySide6.QtGui import QIcon, QPalette
            from PySide6.QtWidgets import QComboBox, QStyle, QStyleOptionComboBox, QStylePainter

            class Center(QObject):
                def eventFilter(self, combo, event):
                    if event.type() != QEvent.Type.Paint or not isinstance(combo, QComboBox) or combo.isEditable():
                        return False
                    painter = QStylePainter(combo)
                    option = QStyleOptionComboBox()
                    combo.initStyleOption(option)
                    text = option.currentText
                    option.currentText = ''
                    option.currentIcon = QIcon()
                    painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option)
                    room = combo.rect().adjusted(30, 0, -30, 0)  # the arrow takes 30 px on the right: the same on the left
                    text = combo.fontMetrics().elidedText(text, Qt.TextElideMode.ElideRight, max(10, room.width()))
                    painter.drawItemText(room, Qt.AlignmentFlag.AlignCenter, option.palette, combo.isEnabled(), text,
                                         QPalette.ColorRole.ButtonText)
                    painter.end()
                    return True

            cls.filter = Center()
        return cls.filter


def center_combo(combo):
    """Draw the choice of a (not editable) combo box centred; returns the combo box."""
    if combo is not None and not combo.property('quail_center'):
        combo.installEventFilter(_CenteredCombo.get())
        combo.setProperty('quail_center', True)
    return combo


ROW_HEIGHT = 32  # a row of the open list of a combo box — 6 px + text 20 px + 6 px (app.style_combo)


def combo_row_delegate(view):
    """The rows of the list were laid out at the height of the text alone while
    the style sheet of the list painted each item 32 px high (padding 6 px, min-height 20 px) and the popup was sized
    for those — on Windows the size of an item does not take the style sheet of the view. The delegate gives each row
    at least ROW_HEIGHT and the height of the text with that padding; on macOS, where the style sheet was taken, the
    rows stay as they were."""
    from PySide6.QtWidgets import QStyledItemDelegate

    class RowDelegate(QStyledItemDelegate):
        def sizeHint(self, option, index):
            size = super().sizeHint(option, index)
            size.setHeight(max(size.height(), option.fontMetrics.height() + 12, ROW_HEIGHT))
            return size

    return RowDelegate(view)


class _WidePopup:
    """The open list of a combo box is as wide as its longest item, not as the field: long items are not cut."""

    filter = None

    @classmethod
    def get(cls):
        if cls.filter is None:
            from PySide6.QtCore import QEvent, QObject

            class Wide(QObject):
                def eventFilter(self, popup, event):
                    if event.type() == QEvent.Type.Show:
                        view = popup.property('quail_view')
                        if view is not None:
                            wanted = view.sizeHintForColumn(0) + 2 * view.frameWidth() + 28
                            if view.verticalScrollBar().isVisible():
                                wanted += view.verticalScrollBar().width()
                            if wanted > popup.width():
                                popup.resize(wanted, popup.height())
                    return False

            cls.filter = Wide()
        return cls.filter


def wide_popup(combo):
    """The list of the combo box opens at least as wide as its longest item; returns the combo box."""
    popup = combo.view().window()
    if popup is not combo.window() and not popup.property('quail_wide'):
        popup.setProperty('quail_view', combo.view())
        popup.installEventFilter(_WidePopup.get())
        popup.setProperty('quail_wide', True)
    return combo


PICTURES_KEY = 'pictures_dir'  # QSettings key: the folder of the last saved picture


def pictures_folder(preferences=None):
    """Where a new picture is offered first: the last folder used, else the system Pictures folder, else home.

    Pictures are never offered inside the program folder: it may be read-only (an app bundle) and is
    not the user's place for documents.
    """
    candidates = [preferences.value(PICTURES_KEY, '') if preferences is not None else '']
    candidates.append(QStandardPaths.writableLocation(QStandardPaths.StandardLocation.PicturesLocation))
    for folder in candidates:
        if folder and Path(folder).is_dir():
            return Path(folder)
    return Path.home()


def ask_picture_path(parent, title, name, suffix, preferences=None):
    """Ask where to save a picture; returns a Path ending in suffix ('.png', '.gif'), or None if cancelled.

    name is the suggested file name without the suffix; the chosen folder is remembered in preferences.
    """
    pattern = f'{suffix[1:].upper()} (*{suffix})'
    chosen, _ = QFileDialog.getSaveFileName(parent, title, str(pictures_folder(preferences) / (name + suffix)), pattern)
    if not chosen:
        return None
    path = Path(chosen)
    if path.suffix.lower() != suffix:
        path = path.with_name(path.name + suffix)
    if preferences is not None:
        preferences.setValue(PICTURES_KEY, str(path.parent))
    return path


def action_button(text, callback, name):
    """An icon button that unfolds into icon + text on hover (azimuth.controls.ExpandingButton)."""
    from azimuth.controls import ExpandingButton

    return ExpandingButton(text, callback, name)


def icon_button(text, callback, name):
    """The same button that never unfolds — only its icon, the text in the tooltip (Sextant)."""
    item = action_button(text, callback, name)
    item.foldable = False
    return item


def menu_font_family():
    """The menus («Файл», «Правка», context menus, the lists of choices) use the system font of the platform
    (San Francisco on macOS, Segoe UI on Windows) — the typeface of the panel looked out of place in them."""
    from PySide6.QtGui import QFontDatabase

    family = QFontDatabase.systemFont(QFontDatabase.SystemFont.GeneralFont).family()
    return family or 'Helvetica Neue'


def _segment_class():
    from PySide6.QtCore import QEasingCurve, QRectF, QSize, Qt, QVariantAnimation
    from PySide6.QtGui import QColor, QFont, QFontMetrics, QIcon, QPainter, QPen
    from PySide6.QtWidgets import QAbstractButton

    class _SegmentButton(QAbstractButton):
        """One choice of a row of choices («Этот компьютер» / «Сервер»): the chosen one shows its icon and its
        name, the others only the icon; the change of width is animated (SLIDE_MS) and the name fades in with it."""

        SLIDE_MS = 200
        HEIGHT = 32
        SMALL = 36

        def __init__(self, text, glyph, tooltip='', parent=None):
            super().__init__(parent)
            self.setText(text)
            self.glyph = glyph
            self.dark = None  # told by the theme of the program
            self.progress = 0.0
            self.expanded = False
            self.setCheckable(True)
            self.setToolTip(tooltip or text)
            self.setAccessibleName(text)
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.setFixedSize(self.SMALL, self.HEIGHT)
            self.anim = QVariantAnimation(self)
            self.anim.setEasingCurve(QEasingCurve.Type.InOutCubic)
            self.anim.valueChanged.connect(self._step)

        def _font(self):
            f = QFont(self.font())
            f.setWeight(QFont.Weight.DemiBold)
            return f

        def full_width(self):
            return self.SMALL + QFontMetrics(self._font()).horizontalAdvance(self.text()) + 10

        def sizeHint(self):
            return QSize(self.width(), self.HEIGHT)

        def set_expanded(self, on, animate=True):
            self.expanded = bool(on)
            target = 1.0 if on else 0.0
            self.anim.stop()
            if animate and self.isVisible():
                self.anim.setStartValue(self.progress)
                self.anim.setEndValue(target)
                self.anim.setDuration(max(1, int(self.SLIDE_MS * abs(target - self.progress))))
                self.anim.start()
            else:
                self._step(target)

        def _step(self, value):
            self.progress = float(value)
            self.setFixedWidth(round(self.SMALL + (self.full_width() - self.SMALL) * self.progress))
            self.update()

        def paintEvent(self, event):
            dark = self.dark if self.dark is not None else self.palette().window().color().lightness() < 128
            on = self.isChecked()
            if on:
                back, line, ink = ('#26364f', '#6ea2f0', '#6ea2f0') if dark else ('#e4ecf8', '#2a62b8', '#2a62b8')
            else:
                back = ('#1d2734' if dark else '#eef2f7') if self.underMouse() else None
                line, ink = ('#34486b', '#c3cdd9') if dark else ('#c3cdd9', '#3f4d61')
            p = QPainter(self)
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
            p.setPen(QPen(QColor(line), 1.0))
            p.setBrush(QColor(back) if back else Qt.BrushStyle.NoBrush)
            p.drawRoundedRect(QRectF(self.rect()).adjusted(0.5, 0.5, -0.5, -0.5), 7, 7)
            from azimuth.icons import icon

            size = 18
            from PySide6.QtCore import QRect

            icon(self.glyph).paint(p, QRect(round((self.SMALL - size) / 2), round((self.HEIGHT - size) / 2), size, size),
                                   Qt.AlignmentFlag.AlignCenter, QIcon.Mode.Normal,
                                   QIcon.State.On if on else QIcon.State.Off)
            if self.progress > 0.02:
                colour = QColor(ink)
                colour.setAlphaF(max(0.0, min(1.0, (self.progress - 0.2) / 0.8)))
                p.setPen(colour)
                p.setFont(self._font())
                p.setClipRect(QRectF(0, 0, self.width() - 4, self.height()))
                p.drawText(QRectF(self.SMALL - 4, 0, self.full_width(), self.height()),
                           Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self.text())
            p.end()

        def enterEvent(self, event):
            self.update()
            super().enterEvent(event)

        def leaveEvent(self, event):
            self.update()
            super().leaveEvent(event)

    return _SegmentButton


SegmentButton = _segment_class()


def frame_plot(painter, widget, radius=6):
    """A thin rounded border in the colour of the lines of
    the theme around the plot, drawn after its background."""
    from PySide6.QtCore import QRectF, Qt
    from PySide6.QtGui import QColor, QPainter, QPen

    dark = widget.palette().base().color().lightness() < 128
    painter.save()
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setPen(QPen(QColor('#3a4452' if dark else '#cfd5de'), 1))
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.drawRoundedRect(QRectF(widget.rect()).adjusted(0.5, 0.5, -0.5, -0.5), radius, radius)
    painter.restore()


def flow_layout(spacing=8):
    """A layout that puts its widgets in rows and goes on to the next row when they no longer
    fit (the FlowLayout of the Qt examples); hidden widgets take no place."""
    from PySide6.QtCore import QPoint, QRect, QSize, Qt
    from PySide6.QtWidgets import QLayout

    class FlowLayout(QLayout):
        def __init__(self):
            super().__init__()
            self._items = []
            self.setSpacing(spacing)
            self.setContentsMargins(0, 0, 0, 0)

        def addItem(self, item):
            self._items.append(item)

        def count(self):
            return len(self._items)

        def itemAt(self, index):
            return self._items[index] if 0 <= index < len(self._items) else None

        def takeAt(self, index):
            return self._items.pop(index) if 0 <= index < len(self._items) else None

        def expandingDirections(self):
            return Qt.Orientation(0)

        def hasHeightForWidth(self):
            return True

        def heightForWidth(self, width):
            return self._place(QRect(0, 0, width, 0), apply=False)

        def setGeometry(self, rect):
            super().setGeometry(rect)
            self._place(rect, apply=True)

        def sizeHint(self):
            return self.minimumSize()

        def minimumSize(self):
            size = QSize()
            for item in self._shown():
                size = size.expandedTo(item.minimumSize())
            m = self.contentsMargins()
            return size + QSize(m.left() + m.right(), m.top() + m.bottom())

        def _shown(self):
            return [item for item in self._items if not (item.widget() is not None and item.widget().isHidden())]

        def _place(self, rect, apply):
            m = self.contentsMargins()
            area = rect.adjusted(m.left(), m.top(), -m.right(), -m.bottom())
            x, y, line = area.x(), area.y(), 0
            gap = self.spacing()
            for item in self._shown():
                hint = item.sizeHint()
                if x > area.x() and x + hint.width() > area.right() + 1:
                    x, y, line = area.x(), y + line + gap, 0
                if apply:
                    item.setGeometry(QRect(QPoint(x, y), hint))
                x += hint.width() + gap
                line = max(line, hint.height())
            return y + line - rect.y() + m.bottom()

    return FlowLayout()


def thin_separators(combo):
    """The separators of the list of a combo box (insertSeparator) drawn as a thin line in the colour of the
    borders of the program (#cfd5de, dark #3a4452) — the style sheet of the list left them an empty row."""
    from PySide6.QtCore import QSize, Qt
    from PySide6.QtGui import QColor, QPen
    from PySide6.QtWidgets import QStyledItemDelegate

    class Delegate(QStyledItemDelegate):
        @staticmethod
        def is_separator(index):
            return index.data(Qt.ItemDataRole.AccessibleDescriptionRole) == 'separator'

        def paint(self, painter, option, index):
            if not self.is_separator(index):
                return super().paint(painter, option, index)
            dark = option.palette.window().color().lightness() < 128
            painter.save()
            painter.setPen(QPen(QColor('#3a4452' if dark else '#cfd5de'), 1))
            y = option.rect.center().y()
            painter.drawLine(option.rect.left() + 8, y, option.rect.right() - 8, y)
            painter.restore()
            return None

        def sizeHint(self, option, index):
            if self.is_separator(index):
                return QSize(option.rect.width(), 9)
            return super().sizeHint(option, index)

    view = combo.view()
    # the class is made anew at each call: the delegate set before is known by its name (each call of
    # crystal_mode.sync_programs gave the list a new one)
    if view.itemDelegate() is None or view.itemDelegate().objectName() != 'thinSeparators':
        delegate = Delegate(view)
        delegate.setObjectName('thinSeparators')
        view.setItemDelegate(delegate)
    return view.itemDelegate()


def align_form_labels(*forms):
    """The column of the captions of
    several QFormLayout of one width — that of the widest caption of them all (hidden rows too, so that it does not jump
    when a task shows its rows): the fields of the pages start at one place. Returns the width."""
    from PySide6.QtWidgets import QFormLayout

    labels = []
    for form in forms:
        if form is None:
            continue
        for row in range(form.rowCount()):
            item = form.itemAt(row, QFormLayout.ItemRole.LabelRole)
            if item is not None and item.widget() is not None:
                labels.append(item.widget())
    if not labels:
        return 0
    width = max(label.sizeHint().width() for label in labels)
    for label in labels:
        label.setMinimumWidth(width)
    return width


