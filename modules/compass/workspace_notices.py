"""The messages of the window of Compass: the pill over the model, the line of a work going on, the pill over the
foot of a page, and where the pill is placed. Methods of CompassWorkspace (self is the window), kept here to make
workspace.py shorter.

Split off modules/compass/workspace.py (0.222.30).
"""



def notify(self, text, ms=8000):
    """A short message over the bottom of the model of Compass (a pill instead of the status line)."""
    # the pill of the
    # model only while the model is on screen — on «Координаты» the field (its parent) is hidden, and so was the
    # message; then the pill of the page
    field = self.notice.parentWidget() if hasattr(self, 'notice') else None
    # isVisibleTo, not isVisible — a window not yet on screen (a test, the start) has its field shown too
    if hasattr(self, 'notice') and self.stack.currentIndex() == 0 and (field is None or field.isVisibleTo(self)):
        self.notice.setText(text)
        self.place_notice()
        self.notice.show()
        self.notice.raise_()
        self.notice_timer.start(ms)
    else:  # the pill of the page
        self.page_notify(text, ms)


def busy_status(self, text, kind=None):
    """The line of a
    work going on (run_waiting, the quick xtb) on a pill of its own — over the model of Compass, at the foot of the
    other pages; the messages (notify) stand above it. text '' — it goes. Returns the pill (None when it went)."""
    from PySide6.QtCore import QPoint, Qt
    from PySide6.QtWidgets import QLabel

    stack = getattr(self, 'stack', None)
    page = stack.currentIndex() if stack is not None else 0
    use = 'model' if page == 0 and getattr(self, 'notice', None) is not None else 'page'
    pills = self.__dict__.setdefault('_busy_pills', {})
    for key, pill in pills.items():
        if key != use or not text:
            pill.hide()
            if not text:
                pill.clear()
    if not text:
        self.place_notice()
        return None
    pill = pills.get(use)
    if pill is None:
        parent = self.notice.parentWidget() if use == 'model' else stack
        pill = pills[use] = QLabel(parent)
        pill.setObjectName('toast')
        pill.setWordWrap(True)
        pill.setAlignment(Qt.AlignmentFlag.AlignCenter)
        pill.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        if use == 'page':  # of the page it was shown on (the pill of the model goes with its page)
            stack.currentChanged.connect(lambda *_: pill.hide())
    if kind is None:
        kind = {1: 'sextant', 2: 'spectrum'}.get(page, 'compass')
    busy = 'wide' if kind == 'spectrum' else True
    if pill.property('busy') != busy:
        pill.setProperty('busy', busy)
        pill.style().unpolish(pill)
        pill.style().polish(pill)
    pill.setText(text)
    from azimuth.ui import fit_pill

    if use == 'model':
        field = self.viewer.geometry()
        inset = int(getattr(self.viewer, 'inset', 0) or 0) if getattr(self, 'drawer', None) is not None else 0
        free = max(0, field.width() - inset)
        width, _ = fit_pill(pill, max(160, min(560, free - 48)))
        pill.move(field.x() + inset + (free - width) // 2, field.y() + field.height() - pill.height() - 16)
    else:
        width, _ = fit_pill(pill, max(160, min(640, stack.width() - 48)))
        bottom = stack.height() - 24
        status = getattr(self, 'status_pill', None)  # the status of Spectrum at the foot: over it
        if status is not None and status.isVisible() and stack.isAncestorOf(status):
            bottom = status.mapTo(stack, QPoint(0, 0)).y() - 8
        pill.move((stack.width() - width) // 2, max(0, bottom - pill.height()))
    pill.show()
    pill.raise_()
    self.place_notice()  # a message shown meanwhile goes above it
    return pill


def busy_pill(self, use=None):
    """The pill of a work going on, shown (of the model or of the page), or None."""
    for key, pill in getattr(self, '_busy_pills', {}).items():
        try:
            # shown — not hidden on purpose (isVisible is False also while the window itself is not on screen)
            if (use is None or key == use) and not pill.isHidden() and pill.text():
                return pill
        except RuntimeError:
            continue
    return None


def page_notify(self, text, ms=8000):
    """A short message on a pill over the foot of the page shown (Sextant, Spectrum) — as the message of
    Compass over its model; the status line of the window (a white strip under the page) is not shown any more."""
    from PySide6.QtCore import QPoint, Qt, QTimer
    from PySide6.QtWidgets import QLabel

    holder = getattr(self, 'stack', None)
    if holder is None:
        return
    toast = getattr(self, '_page_toast', None)
    if toast is None:
        toast = self._page_toast = QLabel(holder)
        toast.setObjectName('toast')
        toast.setWordWrap(True)
        toast.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toast.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self._page_toast_timer = QTimer(self)
        self._page_toast_timer.setSingleShot(True)
        self._page_toast_timer.timeout.connect(toast.hide)
        # the pill is of the page it was shown on — another page shown, it goes (a wait of run_waiting tells it
        # again at once)
        holder.currentChanged.connect(lambda *_: self.drop_page_toast())
    if not text:
        toast.hide()
        return
    pill = getattr(self, 'status_pill', None)  # the status of Spectrum shown at the foot
    shown = pill is not None and not pill.isHidden() and holder.currentWidget() is not None
    shown = shown and holder.currentWidget().isAncestorOf(pill)
    if shown and ms <= self.NOTE_MS:  # a line of it
        toast.hide()
        self.status_note(text, ms)
        return
    if shown:  # a long wait (run_waiting) on its pill instead of the status
        self.status_timer.stop()
        pill.hide()
    toast.setText(text)
    from azimuth.ui import fit_pill

    width, _ = fit_pill(toast, max(160, min(640, holder.width() - 48)))  # as wide as its text
    bottom = holder.height() - 24
    pill = getattr(self, 'status_pill', None)  # the status of Spectrum at the foot: the message over it
    if pill is not None and pill.isVisible() and holder.isAncestorOf(pill):
        bottom = pill.mapTo(holder, QPoint(0, 0)).y() - 8
    busy = self.busy_pill('page')  # above the pill of a work going on
    if busy is not None:
        bottom = min(bottom, busy.y() - 8)
    toast.move((holder.width() - width) // 2, max(0, bottom - toast.height()))
    toast.show()
    toast.raise_()
    self._page_toast_timer.start(ms)


def drop_page_toast(self):
    toast = getattr(self, '_page_toast', None)
    if toast is not None:
        self._page_toast_timer.stop()
        toast.hide()


def hide_notice(self):
    self.notice.clear()
    self.notice.hide()


def place_notice(self, animate=False):
    """The pill in the middle of the part of the field that is free — right of the drawer of the
    result when it is open (viewer.inset), moving with it when animate."""
    notice = getattr(self, 'notice', None)
    if notice is None or not notice.text():
        return
    field = self.viewer.geometry()
    inset = int(getattr(self.viewer, 'inset', 0) or 0) if getattr(self, 'drawer', None) is not None else 0
    free = max(0, field.width() - inset)
    from azimuth.ui import fit_pill

    width, _ = fit_pill(notice, max(160, min(560, free - 48)))  # as wide as its text
    from PySide6.QtCore import QPoint

    target = QPoint(field.x() + inset + (free - width) // 2, field.y() + field.height() - notice.height() - 16)
    busy = self.busy_pill('model')  # above the pill of a work going on
    if busy is not None:
        target.setY(min(target.y(), busy.y() - notice.height() - 8))
    motion = getattr(self, '_notice_motion', None)
    if motion is not None:
        motion.stop()
    if animate and notice.isVisible() and notice.pos() != target:
        from PySide6.QtCore import QEasingCurve, QPropertyAnimation
        from modules.compass.panels.trajectory_drawer import SLIDE_MS

        motion = QPropertyAnimation(notice, b'pos', notice)
        motion.setDuration(SLIDE_MS)
        motion.setEasingCurve(QEasingCurve.Type.OutCubic if inset else QEasingCurve.Type.InOutCubic)
        motion.setStartValue(notice.pos())
        motion.setEndValue(target)
        self._notice_motion = motion
        motion.start()
    else:
        notice.move(target)
