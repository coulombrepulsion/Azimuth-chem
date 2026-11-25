"""The small windows and the placing of windows in Azimuth: «?» with its popup of help, the echo of a status, the
ornaments frozen while a window moves, a dialog kept in the centre of its owner, a pill fitted to its text, «Скопировано».

Split off azimuth/ui.py (0.222.30); azimuth.ui still names them.
"""

from PySide6.QtWidgets import QLabel


HELP_WIDTH = 340  # px: the column of the text of «?»


def help_button(text, name=''):
    """«?» in the style of the program (QToolButton#helpButton, as by the input file of Sextant) — the
    explanation is shown by a click (and under the pointer), it takes no room of the page. .help — the text."""
    from PySide6.QtCore import QEvent, QObject, Qt
    from PySide6.QtWidgets import QToolButton

    item = QToolButton()
    item.setObjectName('helpButton')
    item.setText('?')
    item.setFixedSize(22, 22)
    item.setCursor(Qt.CursorShape.PointingHandCursor)
    item.setAccessibleName(name or text[:60])
    # a column of HELP_WIDTH
    # px, its paragraphs apart (rich text: a plain tooltip is one line as wide as its longest paragraph)
    from html import escape

    paragraphs = ''.join(f'<p style="margin: 0 0 6px 0;">{escape(part).replace(chr(10), "<br>")}</p>'
                         for part in text.split('\n\n'))
    item.setToolTip(f'<table width="{HELP_WIDTH}"><tr><td>{paragraphs}</td></tr></table>')
    item.help = text
    # a click opens a panel that stays (show_help) — the tooltip shown by a click went at the first move
    item.clicked.connect(lambda: show_help(item))

    class Quiet(QObject):  # its tooltip not over its own open panel
        def eventFilter(self, obj, event):
            shown = _HelpPopup.shown
            return event.type() == QEvent.Type.ToolTip and shown is not None and shown[1] is item

    item._quiet = Quiet(item)
    item.installEventFilter(item._quiet)
    return item


class _HelpPopup:
    """The panel of a «?»: one at a time; closed by a click past it, Esc, or a second click on its button."""

    shown = None  # (popup, button)
    closed_at = (None, 0.0)  # (button, monotonic) — the press on the button that closed it must not open it again


def show_help(button, text=None):
    """The explanation of a «?» (button.toolTip() unless text) in a panel under the button that stays
    until a click past it, Esc or another click on the button (a popup window: QToolTip.showText closed at the first
    move of the pointer, and on a Mac at once). Its own tooltip is not shown on the way. Returns the popup, or None
    when the click closed it."""
    import time

    from PySide6.QtCore import QEvent, QObject, QPoint, Qt
    from PySide6.QtGui import QCursor
    from PySide6.QtWidgets import QApplication, QFrame, QLabel, QToolTip, QVBoxLayout

    last, when = _HelpPopup.closed_at
    if last is button and time.monotonic() - when < 0.35:  # the press on «?» closed it — this click is that one
        _HelpPopup.closed_at = (None, 0.0)
        return None
    old = _HelpPopup.shown
    if old is not None:
        try:
            old[0].close()
        except RuntimeError:
            pass
    words = text if text is not None else button.toolTip()
    popup = QFrame(button.window(), Qt.WindowType.Popup | Qt.WindowType.FramelessWindowHint)
    popup.setObjectName('helpPopup')
    popup.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
    palette = QApplication.palette()
    back, fore = palette.toolTipBase().color().name(), palette.toolTipText().color().name()
    popup.setStyleSheet(f'QFrame#helpPopup {{background: {back}; border: 1px solid rgba(120, 140, 170, 0.6); '
                        f'border-radius: 6px;}} QFrame#helpPopup QLabel {{color: {fore}; background: transparent;}}')
    lay = QVBoxLayout(popup)
    lay.setContentsMargins(10, 8, 10, 8)
    label = QLabel(words)
    label.setWordWrap(True)
    label.setTextFormat(Qt.TextFormat.AutoText)
    label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    label.setFixedWidth(HELP_WIDTH)
    lay.addWidget(label)
    popup.adjustSize()
    point = button.mapToGlobal(QPoint(0, button.height() + 2))
    screen = button.screen()
    if screen is not None:
        room = screen.availableGeometry()
        size = popup.sizeHint()
        x = min(max(room.left(), point.x()), room.right() - size.width())
        y = point.y() if point.y() + size.height() <= room.bottom() else \
            max(room.top(), button.mapToGlobal(QPoint(0, 0)).y() - size.height() - 2)
        point = QPoint(x, y)
    popup.move(point)

    class Closing(QObject):
        def eventFilter(self, obj, event):
            if event.type() == QEvent.Type.Close:
                try:
                    under = QApplication.widgetAt(QCursor.pos())
                except RuntimeError:
                    under = None
                if under is button:
                    _HelpPopup.closed_at = (button, time.monotonic())
                if _HelpPopup.shown is not None and _HelpPopup.shown[0] is popup:
                    _HelpPopup.shown = None
            return False

    closing = Closing(popup)
    popup.installEventFilter(closing)
    _HelpPopup.shown = (popup, button)
    QToolTip.hideText()  # the tooltip of the button under the pointer away before the panel comes
    popup.show()
    return popup


class StatusEcho(QLabel):
    """A line of messages that is never
    shown in the page — what is set is told by the window (notify: the pill over the model of Compass, or the status
    line), for a while; in a window that has neither (a dialog) it stands in its place as before. text() keeps the
    last message."""

    MS = 9000

    def __init__(self, *args):
        super().__init__(*args)
        self.setWordWrap(True)
        self.hide()

    def setText(self, text):
        super().setText(text)
        try:
            self._tell(text)
        except RuntimeError:  # the window being deleted
            pass

    def teller(self):
        """The nearest widget above with notify(), else
        the window."""
        widget = self.parentWidget()
        while widget is not None:
            if hasattr(widget, 'notify') and callable(widget.notify):
                return widget
            widget = widget.parentWidget()
        return self.window()

    def _tell(self, text):
        top = self.teller()
        if top is self:
            return
        if hasattr(top, 'notify'):
            if text:
                top.notify(text, self.MS)
            self.hide()
        elif hasattr(top, 'statusBar'):
            if text:
                top.statusBar().showMessage(text, self.MS)
            self.hide()
        else:
            self.setVisible(bool(text))

    def setVisible(self, visible):
        if visible:  # Qt hides it while the window is deleted: nothing of the window is asked then
            try:
                top = self.teller()
                if top is not self and (hasattr(top, 'notify') or hasattr(top, 'statusBar')):
                    visible = False  # told by the window, never a line of the page
            except RuntimeError:
                visible = False
        super().setVisible(visible)


def freeze_ornaments(widget, frozen=True):
    """The scales of the window of widget drawn as a picture (frozen) or anew — while a panel slides."""
    try:
        window = widget.window()
        from PySide6.QtWidgets import QWidget

        for each in window.findChildren(QWidget):
            act = getattr(each, 'freeze_ornament' if frozen else 'thaw_ornament', None)
            if act is not None:
                act()
    except RuntimeError:
        pass


class DialogCentre:
    """A dialog of the program, the first time it is shown, stands in the middle of the window it belongs to (its
    parent's window, else the active one, else the screen). A dialog with the property keepPlace (one that remembers its
    own place) and the file dialogs are left alone. One filter on the application: install()."""

    _filter = None

    @classmethod
    def install(cls):
        from PySide6.QtCore import QEvent, QObject
        from PySide6.QtWidgets import QApplication, QDialog

        app = QApplication.instance()
        if app is None or cls._filter is not None:
            return cls._filter

        class _Filter(QObject):
            def eventFilter(self, watched, event):
                if event.type() == QEvent.Type.Show and isinstance(watched, QDialog) and centre_first(watched):
                    try:
                        from PySide6.QtCore import QTimer

                        # once more when the window has settled (a size set while it opens, the frame of the system)
                        QTimer.singleShot(0, lambda d=watched: _recentre(d))
                    except RuntimeError:
                        pass
                return False

        cls._filter = _Filter(app)
        app.installEventFilter(cls._filter)
        return cls._filter


def centre_first(dialog):
    """The dialog centred the first time it shows (True), or left where it is: shown before, a file dialog, one with
    keepPlace. Called by DialogCentre and by the slide of azimuth.polish (whichever filter sees the showing first)."""
    from PySide6.QtWidgets import QFileDialog

    from PySide6.QtCore import Qt

    from azimuth.polish import is_sheet

    # a window-modal dialog (QMessageBox.open)
    # is a sheet of the system on macOS — moved, it was not seen at all; native dialogs are left alone too
    if (not dialog.isWindow() or isinstance(dialog, QFileDialog) or dialog.property('keepPlace')
            or dialog.property('azimuthCentred') or is_sheet(dialog.windowModality())
            or dialog.testAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen)):
        return False
    dialog.setProperty('azimuthCentred', True)
    try:
        centre(dialog)
    except RuntimeError:
        return False
    return True


def centre(dialog):
    """The dialog in the middle of its window (see DialogCentre), kept on the screen."""
    from PySide6.QtWidgets import QApplication

    # the size the window takes when shown — its layout asks
    # for more than the size given before (560 px; it became ~880) and it grew to the right of the place found
    layout = dialog.layout()
    if layout is not None:
        layout.activate()
    from PySide6.QtWidgets import QWidget

    # the methods of the widget, not its attributes
    dialog.resize(QWidget.size(dialog).expandedTo(QWidget.minimumSizeHint(dialog)))
    parent = dialog.parentWidget()
    anchor = parent.window() if parent is not None else QApplication.activeWindow()
    if anchor is dialog:
        anchor = None
    frame = dialog.frameGeometry()
    if anchor is not None and anchor.isVisible():
        middle = anchor.frameGeometry().center()
        screen = anchor.screen()
    else:
        screen = dialog.screen() or QApplication.primaryScreen()
        middle = screen.availableGeometry().center() if screen is not None else frame.center()
    frame.moveCenter(middle)
    if screen is not None:
        room = screen.availableGeometry()
        frame.moveLeft(max(room.left(), min(frame.left(), room.right() - frame.width())))
        frame.moveTop(max(room.top(), min(frame.top(), room.bottom() - frame.height())))
    dialog.move(frame.topLeft())


SIDE, TOP = 20, 10  # px: the air between the words of a pill and its edges


def fit_pill(label, widest, narrowest=120):
    """A pill of a message (a QLabel with word wrap, its padding in the style) as wide as its text — one line when it
    fits in widest, else widest and wrapped; as high as its lines. Returns (width, height). Measured by the font and the
    padding of the style themselves (the width of the label less its contentsRect), not by the size hint of a wrapping
    label."""
    from PySide6.QtCore import QRect, Qt

    label.ensurePolished()
    # the room of the sign of waiting at the left (the compass
    # or the sextant of 20 px, the spectrum of 34 px, at 14 px from the edge, then 12 px of air) is a margin of the
    # label — the padding of the style was not kept by the centred text, which stood right by the sign
    busy = label.property('busy')
    extra = (14 + 34 + 12 - SIDE) if busy == 'wide' else (14 + 20 + 12 - SIDE) if busy else 0
    # the margins of the words are set here whole — the margins set for the sign replaced the padding of the
    # style (Qt keeps the padding of a style sheet in the contents margins), and a wrapped text went edge to edge
    label.setContentsMargins(SIDE + extra, TOP, SIDE, TOP)
    pad_w, pad_h = 2 * SIDE + extra + 2, 2 * TOP + 2  # and 1 px of the frame on each side
    metrics = label.fontMetrics()
    lines = label.text().split('\n') or ['']
    text_w = max(metrics.horizontalAdvance(line) for line in lines)
    natural = text_w + pad_w + 6
    width = max(narrowest, min(widest, natural))
    if natural <= widest:
        height = metrics.height() * len(lines) + pad_h
    else:
        box = metrics.boundingRect(QRect(0, 0, max(1, width - pad_w - 6), 100000),
                                   int(Qt.TextFlag.TextWordWrap) | int(Qt.AlignmentFlag.AlignHCenter), label.text())
        height = box.height() + pad_h
    height = max(height, metrics.height() + pad_h)
    label.setFixedSize(width, height)
    return width, height


def _recentre(dialog):
    try:
        if dialog.isVisible() and not dialog.property('azimuthSliding'):
            centre(dialog)
    except RuntimeError:
        pass


def copied(widget, what='', button=None):
    """«Скопировано: what» in the message line of the window of widget
    (the first parent with notify); the button pressed says «✓ Скопировано» for a moment too — a window over the main
    one (a dialog) covers its message line. Without a window with notify — a tooltip at the widget. -> the message."""
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QToolTip

    from azimuth.i18n import tr

    message = tr('Скопировано: {}.').format(what) if what else tr('Скопировано в буфер обмена.')
    if button is not None:
        try:
            kept = button.text()
            if kept:  # a button with words; an icon alone keeps its size — its tooltip says it
                button.setText('✓ ' + tr('Скопировано'))
                button.setMinimumWidth(max(button.minimumWidth(), button.sizeHint().width()))
                QTimer.singleShot(1500, lambda: _restore_text(button, kept))
            else:
                QToolTip.showText(button.mapToGlobal(button.rect().bottomLeft()), message, button)
        except RuntimeError:
            pass
    owner = widget
    while owner is not None:
        notify = getattr(owner, 'notify', None)
        if callable(notify):
            try:
                notify(message, 4000)
                return message
            except TypeError:
                pass
        owner = owner.parentWidget() if hasattr(owner, 'parentWidget') else None
    if button is None and widget is not None:
        try:
            QToolTip.showText(widget.mapToGlobal(widget.rect().center()), message, widget)
        except RuntimeError:
            pass
    return message


def _restore_text(button, text):
    try:
        button.setText(text)
    except RuntimeError:  # the window was closed meanwhile
        pass
