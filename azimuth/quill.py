"""Quill in the windows of the program — since 0.247.0 the pictures of states in thin lines (azimuth/state_icons.py).

§0 STATE
    0.247.0 (2026-11-27, the owner: «квил в самой программе не нужна. Пусть она остается в Атласе как помощник, а в
    программе ее убрать и заменить на более минималистичные картинки/иконки»): the names and the functions stay, the
    pictures are those of state_icons; the dialogs show a picture of ICON_SIDE px at the top of a narrow column on the
    left; nothing is mirrored; the empty places show a smaller picture. The files of assets/quill/ stay for the site.
§1 PURPOSE
    The pictures of Quill chosen by the user (assets/quill/, brief: docs/art/QUAIL_ART.md) in the places of the
    program: the window of the calculation when it is over, the dialogs «Сохранить изменения перед выходом?»,
    «Заменить структуру?», «Расчёт ещё не закончен…», the check of the input file, the empty Spectrum.
§2 ALGORITHM
    pixmap(name, size) reads quill-<name>.webp and scales it to size × size logical pixels at the device pixel
    ratio of the screen (sharp on Retina). question() is QMessageBox.question with Quill instead of the system
    icon: a QMessageBox with setIconPixmap. When QMessageBox.question has been replaced by a Python function (the
    stubs of tests/conftest.py, monkeypatch in a test) that function is called instead, so the tests keep
    answering the dialog and no window is opened.
§3 APPLICATIONS azimuth/app.py (closeEvent, confirm_replace), modules/sextant/job_window.py,
    modules/sextant/workspace.py (confirm_input_problems), modules/spectrum/workspace.py (the empty result). The
    calculation failed or stopped and the installer of the programs (Sextant), the program is not found (Sextant), the
    empty field of Compass, the journal of changes (hub/about.py), the Atlas that did not start
    (modules/atlas/panel.py). Warning() — «Не удалось выполнить действие» of all sections (Studio.error,
    spectra_view.show_error, the windows of Spectrum), a file not read ('file-unreadable'), the conformer search that
    found nothing ('nothing-found', exc.quill), no connection to the server ('offline', ssh.SshError.kind); question()
    with 'delete' — deleting and replacing schemes and fragments, «Закрыть вкладку?»; EmptyNote — the empty pages
    «Орбитали», «Поверхности», «QTAIM», «Частоты» of the drawer ('no-orbitals'), the critical points not found yet and
    the empty tab «NCI» ('no-points'); trimmed_pixmap('sextant-empty') — the card of the calculation without atoms.
§4 SPECIFICATION
    FOLDER; NAMES; path(name) -> Path; pixmap(name, size, ratio=None) -> QPixmap (null when the file is missing;
    mirrored for a name of TURNED_LEFT, turned(name, pixmap));
    set_icon(box, name, fallback, size=ICON) — Quill the whole height of the dialog in a column of SIDE px at
    its left (_Side), the headline, the text, the check box and the buttons at her right (relayout, when the box is
    shown); her height is the height of the text and the buttons, she adds none; no blue edge (it stays on the clouds of
    Quill, paint_edge);
    question(parent, title, text, buttons, default, name) -> StandardButton, warning(…), information(…) — the title
    is the headline.
§5 PROCEDURES - below.
§6 NOTES
    A missing picture never stops a dialog: the system icon is shown instead.
§7 TESTS
    tests/test_gui.py::test_quill_pictures.
§8' ROBUSTNESS
    The pictures are checked by assets-manifest.json like the other assets.
"""

import types

from PySide6.QtCore import QEvent, QObject, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import QFrame, QMessageBox

from .paths import ROOT

FOLDER = ROOT / 'assets' / 'quill'
NAMES = ('calc-done', 'calc-failed', 'calc-stopped', 'save', 'stop-running', 'input-check', 'empty-result', 'empty-model',
         'program-missing', 'install', 'notes',  # the second set ('atlas-error', 'peek' unused — removed)
         'calc-running',  # the animation of a running calculation (animated WebP, 480², 20 s)
         'empty-crystal',  # the empty field of «Компас · Кристалл»
         # the dialogs and the empty places of docs/art/QUAIL_ART_DIALOGS.md
         'error', 'file-unreadable', 'delete', 'no-points', 'no-orbitals', 'nothing-found', 'offline', 'sextant-empty',
         'empty-model-mirrored',  # the empty field of «Компас · Молекула», Quill turned to her bubble
         'install-done', 'update', 'reset', 'info')  # 0.249.1: pictures of their own, not borrowed (the owner: «И проверь, что иконки не повторяются»)


def path(name):
    return FOLDER / f'quill-{name}.webp'


# these pictures are shown
# turned to the left — mirrored when drawn (pixmap(), the frames of the animation in the window of the calculation),
# the files stay as they were approved (assets/quill/APPROVED.md)
TURNED_LEFT = frozenset()  # 0.247.0: the pictures of states are drawn as they are


def turned(name, image):
    """The picture as the program shows it: mirrored left to right for a name of TURNED_LEFT (a QPixmap)."""
    if name not in TURNED_LEFT or image.isNull():
        return image
    from PySide6.QtGui import QTransform

    ratio = image.devicePixelRatio()
    flipped = image.transformed(QTransform().scale(-1, 1))
    flipped.setDevicePixelRatio(ratio)
    return flipped


def pixmap(name, size, ratio=None):
    """The picture of the state `name` (azimuth/state_icons.py), size × size logical pixels; null for an unknown name."""
    from . import state_icons

    if ratio is None:
        app = QGuiApplication.instance()
        ratio = app.devicePixelRatio() if app is not None else 1.0
    return turned(name, state_icons.pixmap(name, size, max(1.0, float(ratio))))


# a dialog with Quill has a blue edge on the side away from her (Quill stands on the left, the edge is on
# the right), as the card «Квил знает» of the Atlas has its blue side; the blue of the buttons of the theme
EDGE = 3  # thinner by the wish of the user (4 px, as in the Atlas; 5)
EDGE_COLOR = {'light': '#2a62b8', 'dark': '#6ea2f0'}


def edge_color(background):
    """The blue of the edge for a card of this background colour (a dark card: the light blue of the dark theme)."""
    from PySide6.QtGui import QColor

    return QColor(EDGE_COLOR['dark' if QColor(background).lightness() < 128 else 'light'])


def paint_edge(painter, body, radius, side, background):
    """The blue side of a rounded card as CSS draws «border-left: 4px» with «border-radius»: the band follows
    the rounded corners and thins out into the 1 px border of the top and the bottom (the outer rounded rectangle
    less the inner one, on that side only). body — QRectF of the card, side — 'left' or 'right'.
    The side is cut off by clipping, not by intersecting the paths — the intersection left a seam of no width
    along the cut, which Windows drew as a thin blue line inside the card (the greeting of Quill, the screenshot of the
    user: a vertical line 20 px from the blue side, the whole height of the card)."""
    from PySide6.QtCore import QRectF
    from PySide6.QtGui import QPainterPath

    outer = QPainterPath()
    outer.addRoundedRect(body, radius, radius)
    if side == 'left':
        inner_rect = body.adjusted(EDGE, 1, -1, -1)
        region = QRectF(body.left() - 1, body.top() - 1, radius + EDGE, body.height() + 2)
    else:
        inner_rect = body.adjusted(1, 1, -EDGE, -1)
        region = QRectF(body.right() - radius - EDGE + 1, body.top() - 1, radius + EDGE, body.height() + 2)
    inner = QPainterPath()
    inner.addRoundedRect(inner_rect, max(0.0, radius - EDGE), max(0.0, radius - 1))
    cut = QPainterPath()
    cut.addRect(region)
    painter.save()
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(edge_color(background))
    painter.setClipPath(cut, Qt.ClipOperation.IntersectClip)
    painter.drawPath(outer.subtracted(inner))
    painter.restore()


class _Edge(QObject):
    """Keeps the strip at the right edge of the box, full height, above the content; coloured for the theme."""

    def __init__(self, box):
        super().__init__(box)
        self.box = box
        self.strip = QFrame(box)
        self.strip.setObjectName('quillEdge')
        self.strip.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        box.installEventFilter(self)
        self.place()

    def place(self):
        dark = self.box.palette().window().color().lightness() < 128
        self.strip.setStyleSheet(f'background: {EDGE_COLOR["dark" if dark else "light"]}; border: none;')
        self.strip.setGeometry(self.box.width() - EDGE, 0, EDGE, self.box.height())
        self.strip.raise_()

    def eventFilter(self, watched, event):
        if event.type() in (QEvent.Type.Resize, QEvent.Type.Show, QEvent.Type.PaletteChange, QEvent.Type.StyleChange):
            self.place()
        return False


def mark_edge(box):
    if getattr(box, '_quill_edge', None) is None:
        box._quill_edge = _Edge(box)
    return box._quill_edge.strip


ICON = 44  # the picture given to the box of Qt (its icon label — hidden when the picture stands at the side, _Side)
ICON_SIDE = 48  # px: the picture of the state at the top of its column (0.247.0)
SIDE = 64  # the column of the picture at the left of a dialog, px
SIDE_MIN = 64
TEXT_WIDTH = 360  # the text of a dialog with Quill: no narrower than this
WIDTH = SIDE + TEXT_WIDTH  # the window of a dialog with Quill at least this wide
_ICON_LABEL, _TEXT_LABEL, _INFO_LABEL = 'qt_msgboxex_icon_label', 'qt_msgbox_label', 'qt_msgbox_informativelabel'
_BUTTONS = 'qt_msgbox_buttonbox'


class _Side(QFrame):
    """Quill in a column of
    SIDE px at the left, as tall as the rows beside her — the headline, the text, the check box, the buttons — and no
    taller: she asks for no height (the text and the buttons decide the height of the window) and is drawn to fit the
    height she is given, without her clear edges."""

    def __init__(self, name, parent=None):
        from PySide6.QtWidgets import QSizePolicy

        super().__init__(parent)
        self.name = name
        self.setObjectName('quillSide')
        self.setProperty('quill', True)  # she hides the hub's faint scales
        self.setFixedWidth(SIDE)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Ignored)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)

    def sizeHint(self):
        from PySide6.QtCore import QSize

        return QSize(self.minimumWidth(), 0)

    def minimumSizeHint(self):
        return self.sizeHint()

    def art(self):
        """The picture of the state, ICON_SIDE px (0.247.0: no more drawn to the height of the text)."""
        return pixmap(self.name, ICON_SIDE)

    def paintEvent(self, event):
        from PySide6.QtCore import QRectF
        from PySide6.QtGui import QPainter

        picture = self.art()
        if picture.isNull() or self.height() < 8:
            return
        side = min(ICON_SIDE, self.width(), self.height())
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        painter.drawPixmap(QRectF((self.width() - side) / 2, 2, side, side), picture,
                           QRectF(0, 0, picture.width(), picture.height()))
        painter.end()


class _Compact(QObject):
    """The dialog laid out when it is shown (relayout). No blue edge; Quill the whole height at the left (_Side), the
    rest at her right."""

    def __init__(self, box):
        super().__init__(box)
        self.box = box
        self.done = False
        box.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Show and not self.done:
            self.done = relayout(self.box)
        return False


def relayout(box):
    """The grid of the QMessageBox rearranged (see _Side, _Compact): Quill in column 0 over all the rows, the headline,
    the text, the check box and the buttons one under another in column 2; False when the layout is not the grid of
    Qt."""
    from PySide6.QtWidgets import QCheckBox, QDialogButtonBox, QGridLayout, QLabel, QSizePolicy, QSpacerItem

    grid = box.layout()
    if not isinstance(grid, QGridLayout):
        return False
    icon = box.findChild(QLabel, _ICON_LABEL)
    text = box.findChild(QLabel, _TEXT_LABEL)
    if icon is None or text is None or grid.indexOf(icon) < 0 or grid.indexOf(text) < 0:
        return False
    info = box.findChild(QLabel, _INFO_LABEL)
    buttons = box.findChild(QDialogButtonBox, _BUTTONS)
    column = [w for w in (text, info, box.findChild(QCheckBox)) if w is not None and grid.indexOf(w) >= 0]
    if buttons is not None and grid.indexOf(buttons) >= 0:
        column.append(buttons)
    grid.removeWidget(icon)
    icon.hide()  # the small picture of the box of Qt: Quill stands at the side instead
    for widget in column:
        grid.removeWidget(widget)
    for row, widget in enumerate(column):
        grid.addWidget(widget, row, 2, 1, 1)
    side = getattr(box, '_quill_side', None)
    if side is None:
        side = box._quill_side = _Side(getattr(box, '_quill_name', 'save'), box)
    side.setFixedWidth(SIDE)  # the picture of the state at the top of a narrow column (0.247.0)
    grid.addWidget(side, 0, 0, len(column), 1)
    grid.addItem(QSpacerItem(TEXT_WIDTH, 0, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed), len(column), 2)
    grid.setColumnStretch(0, 0)
    grid.setColumnStretch(2, 1)
    for row in range(grid.rowCount()):  # every row as tall as its own text: none stretched to make room for Quill
        grid.setRowStretch(row, 0)
    return True


def set_icon(box, name, fallback, size=ICON):
    picture = pixmap(name, size)
    if picture.isNull():
        box.setIcon(fallback)
    else:
        box.setIconPixmap(picture)
        box._quill_name = name
        if getattr(box, '_quill_compact', None) is None:
            box._quill_compact = _Compact(box)


def split_message(text, limit=140):
    """(headline, detail) of a message: a long one shows its first sentence in bold (the text of the box) and
    the rest in the plain font under it (its informative text) — a whole paragraph in bold was hard to read."""
    text = str(text)
    if len(text) <= 110:
        return text, ''
    # the end of a sentence: not «а. е. м.» or «т. е.» (a one-letter word before the point), not before 25 letters
    dots = [i for i in range(25, min(len(text), limit + 1)) if text.startswith('. ', i) and text[i - 2] != ' ']
    cut = [i for i in (dots[0] if dots else -1, text.find('\n')) if 0 < i <= limit]
    if not cut:
        return text, ''
    i = min(cut)
    head, rest = text[: i + (1 if text[i] == '.' else 0)], text[i + 1:].strip()
    return (head, rest) if rest else (text, '')


def _fill(box, text):
    head, detail = split_message(text)
    box.setText(head)
    if detail:
        box.setInformativeText(detail)


def headline(box, title, text):
    """The title of a question or a warning is its headline beside Quill (macOS shows no title of a
    dialog), the text under it; a title that is only the name of the program, or none — the first sentence leads, as
    before (_fill)."""
    box.setWindowTitle(title)
    if title and title.strip() not in ('Азимут', 'Azimuth', '方位') and title.strip() != str(text).strip():
        from html import escape

        box.setText(f'<b>{escape(title)}</b>')
        box.setInformativeText(str(text))
    else:
        _fill(box, text)


def warning(parent, title, text, name='error'):
    """QMessageBox.warning with Quill instead of the system triangle (docs/art/QUAIL_ART_DIALOGS.md): 'error' for
    «Не удалось выполнить действие», 'file-unreadable' for a file that was not read, 'nothing-found', 'offline'. A
    replaced QMessageBox.warning (the stubs of the tests) answers instead, as in question()."""
    if isinstance(QMessageBox.warning, types.FunctionType):
        return QMessageBox.warning(parent, title, text)
    box = QMessageBox(parent)
    headline(box, title, text)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    set_icon(box, name, QMessageBox.Icon.Warning)
    box.exec()
    return QMessageBox.StandardButton.Ok


def trimmed(picture):
    """The picture without its clear edges (unused by the pictures of states since 0.247.0)."""
    from PySide6.QtGui import QImage

    if picture.isNull():
        return picture
    image = picture.toImage().convertToFormat(QImage.Format.Format_ARGB32)
    w, h = image.width(), image.height()
    left, top, right, bottom = w, h, -1, -1
    for y in range(0, h, 2):  # every second row and column: enough for the margins, fast in pure Python
        for x in range(0, w, 2):
            if (image.pixel(x, y) >> 24) > 8:
                left, right, top, bottom = min(left, x), max(right, x), min(top, y), max(bottom, y)
    if right < 0:
        return picture
    left, top = max(0, left - 1), max(0, top - 1)
    cut = picture.copy(left, top, min(w, right + 2) - left, min(h, bottom + 2) - top)
    cut.setDevicePixelRatio(picture.devicePixelRatio())
    return cut


_TRIMMED = {}


def trimmed_pixmap(name, size):
    """pixmap(name, size), kept once per picture, size and screen ratio (the pictures of states have their margins
    drawn in: nothing is cut since 0.247.0)."""
    app = QGuiApplication.instance()
    key = (name, size, app.devicePixelRatio() if app is not None else 1.0)
    if key not in _TRIMMED:
        _TRIMMED[key] = pixmap(name, size)
    return _TRIMMED[key]


class EmptyNote(QFrame):
    """An empty place of a page — the picture of the state (72 px) over the grey line of text, both centred
    ('no-points', 'no-orbitals'). Without the picture only the text is shown."""

    def __init__(self, text, name, size=72, parent=None):
        from PySide6.QtWidgets import QLabel, QVBoxLayout

        super().__init__(parent)
        column = QVBoxLayout(self)
        column.setContentsMargins(0, 8, 0, 8)
        column.setSpacing(8)
        self.picture = QLabel(self)  # a parent at once: shown before it, a QLabel is a window of its own for a moment
        self.picture.setProperty('quill', True)  # she hides the hub's faint scales
        self.picture.setAlignment(Qt.AlignmentFlag.AlignCenter)
        art = trimmed_pixmap(name, size)
        self.picture.setVisible(not art.isNull())
        if not art.isNull():
            self.picture.setPixmap(art)
        self.label = QLabel(text)
        self.label.setObjectName('subtitle')
        self.label.setWordWrap(True)
        self.label.setAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        column.addWidget(self.picture)
        column.addWidget(self.label)

    def setText(self, text):
        self.label.setText(text)

    def text(self):
        return self.label.text()


def information(parent, title, text, name='notes'):
    """QMessageBox.information with the picture of the state instead of the system «i» (0.249.1: the dialogs of the
    updates had the system icon). A replaced QMessageBox.information (the tests) answers instead, as in warning()."""
    if isinstance(QMessageBox.information, types.FunctionType):
        return QMessageBox.information(parent, title, text)
    box = QMessageBox(parent)
    headline(box, title, text)
    box.setStandardButtons(QMessageBox.StandardButton.Ok)
    set_icon(box, name, QMessageBox.Icon.Information)
    box.exec()
    return QMessageBox.StandardButton.Ok


def question(parent, title, text, buttons, default, name, labels=None):
    """Labels — {standard button: its own text} («Удалить копию» for Discard)."""
    if isinstance(QMessageBox.question, types.FunctionType):  # replaced (tests): let the replacement answer
        return QMessageBox.question(parent, title, text, buttons, default)
    box = QMessageBox(parent)
    headline(box, title, text)
    box.setStandardButtons(buttons)
    for button, label in (labels or {}).items():
        if box.button(button) is not None:
            box.button(button).setText(label)
    box.setDefaultButton(default)
    set_icon(box, name, QMessageBox.Icon.Question)
    box.exec()
    clicked = box.clickedButton()
    return box.standardButton(clicked) if clicked is not None else QMessageBox.StandardButton.Cancel
