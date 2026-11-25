"""Quill and her speech bubble in the empty field of «Компас · Молекула».

§1 PURPOSE
    While the molecule tab is empty, Quill stands in the lower right corner of the field and says «Попробуй построить
    свою молекулу ✎ или открой новую 📁»; the pencil and the folder are buttons — «Изменение структуры» and
    «Файл → Открыть…». Once a molecule has been built or opened after she was shown, she goes away until the program
    is started again (a press of a button alone does not send her away: the file dialog can be cancelled).
§2 ALGORITHM A child widget of the page over the model (like the drawer): the bubble (a rounded card with a tail to the
    right, towards Quill's head, painted) with two rows «text + glyph button», and Quill
    (assets/quill/quill-empty-model-mirrored.webp, PICTURE px, its clear edges cut off — trimmed), the bubble GAP px
    from her; place(field) puts it into the lower right corner of the field rectangle with a margin; a field too small
    for it hides it (fits()). Colours follow set_dark. «Компас · Кристалл» has its own (kind='crystal'): Quill with the
    unit cell (quill-empty-crystal.webp) in the lower LEFT corner, the bubble to the right of her (its tail to the left,
    the blue side on the right) — «Открой кристалл из файла CIF 📁 или возьми пример 💎» (the folder: «Файл → Открыть
    CIF…», the crystal: «Открыть пример…»).
§4 SPECIFICATION
    QuillHint(parent, on_edit, on_open, kind='model'|'crystal'); side ('right'|'left' — her corner); place(field: QRect)
    -> bool (it fits); set_dark(dark); dismissed (bool); edit_button (the first button: the pencil, or for a crystal
    the folder), open_button (the second), quill (QLabel), bubble (QFrame), text_lines ([QLabel]).
§7 TESTS
    tests/test_gui.py::test_crystal_tab_and_the_empty_field, ::test_crystal_quill_hint.
"""

from PySide6.QtCore import QRectF, QSize, Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QToolButton, QVBoxLayout, QWidget

from azimuth import quill
from azimuth.i18n import tr
from azimuth.icons import icon

PICTURE = 200  # px, Quill (was 78 at the bottom of the right panel, then 150)
MARGIN = 6  # px from the corner of the field to her (the clear edges of the picture are cut off)
GAP = 2  # px between the tail of the bubble and her


def trimmed(pixmap):
    """The picture without its clear edges (the square of quill-*.webp has ~20 % of air left and right): she stands
    right in the corner and the bubble right at her."""
    if pixmap.isNull():
        return pixmap
    import numpy as np

    image = pixmap.toImage().convertToFormat(QImage.Format.Format_ARGB32)  # bytes B, G, R, A
    w, h = image.width(), image.height()
    alpha = np.frombuffer(image.constBits(), np.uint8, count=image.sizeInBytes()).reshape(h, image.bytesPerLine())[:, 3:w * 4:4]
    rows, cols = np.nonzero(alpha > 8)
    if not len(rows):
        return pixmap
    cut = pixmap.copy(int(cols.min()), int(rows.min()), int(cols.max() - cols.min() + 1), int(rows.max() - rows.min() + 1))
    cut.setDevicePixelRatio(pixmap.devicePixelRatio())
    return cut


class Bubble(QFrame):
    TAIL = 12

    def __init__(self, parent=None, side='right'):
        """side: where Quill stands, the tail points there ('left' in the crystals)."""
        super().__init__(parent)
        self.side = side
        self.fill, self.edge = QColor('#ffffff'), QColor('#d8dce3')
        self.setContentsMargins(*((self.TAIL, 0, 0, 0) if side == 'left' else (0, 0, self.TAIL, 0)))

    def set_colors(self, fill, edge):
        self.fill, self.edge = QColor(fill), QColor(edge)
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        t = self.TAIL
        left = self.side == 'left'
        body = QRectF(0.5 + (t if left else 0), 0.5, self.width() - t - 1, self.height() - 1)
        path = QPainterPath()
        path.addRoundedRect(body, 14, 14)
        ty = min(body.bottom() - 18, max(body.top() + 18, body.height() * 0.35))  # towards her head
        tail = QPainterPath()
        base = body.left() + 1 if left else body.right() - 1
        tail.moveTo(base, ty - 9)
        tail.lineTo(0.5 if left else self.width() - 0.5, ty + 2)
        tail.lineTo(base, ty + 7)
        tail.closeSubpath()
        p.setPen(QPen(self.edge, 1))
        p.setBrush(self.fill)
        p.drawPath(path.united(tail))
        # the blue side away from Quill, as the card «Квил знает» of the Atlas
        quill.paint_edge(p, body, 14, 'right' if left else 'left', self.fill)  # round at the corners
        p.end()


KINDS = {  # (picture, her corner, [(text, glyph, tip)])
    # the updated picture — Quill turned to the left, towards her bubble (quill-empty-model-mirrored.webp)
    'model': ('empty-model-mirrored', 'right', [('Попробуй построить свою молекулу', 'edit',
                                        'Изменение структуры · атомы, фрагменты, молекулы из библиотеки'),
                                       ('или открой новую', 'folder', 'Файл → Открыть…')]),
    'crystal': ('empty-crystal', 'left', [('Открой кристалл из файла CIF', 'folder', 'Файл → Открыть CIF…'),
                                          ('или возьми пример', 'crystal', 'Файл → Открыть пример…')]),
}


class QuillHint(QWidget):
    def __init__(self, parent, on_edit, on_open, kind='model'):
        super().__init__(parent)
        name, self.side, texts = KINDS[kind]
        self.kind = kind
        self.setObjectName('quillHintCrystal' if kind == 'crystal' else 'quillHint')
        self.dismissed = False
        self.seen = False  # shown in this run: the first molecule after it sends her away
        self.on_edit, self.on_open = on_edit, on_open
        row = QHBoxLayout(self)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(GAP)
        self.bubble = Bubble(side=self.side)
        lines = QVBoxLayout(self.bubble)
        if self.side == 'left':
            lines.setContentsMargins(16 + Bubble.TAIL, 12, 14, 12)
        else:
            lines.setContentsMargins(16, 12, 14 + Bubble.TAIL, 12)
        lines.setSpacing(4)
        self.text_lines = []
        (first, glyph1, tip1), (second, glyph2, tip2) = texts
        self.edit_button = self._button(glyph1, tr(tip1), self._edit)
        self.open_button = self._button(glyph2, tr(tip2), self._open)
        # Quill speaks to the user on «ты», as everywhere in the program (the pale hint of the field stays on «вы»)
        for text, button in ((tr(first), self.edit_button), (tr(second), self.open_button)):
            line = QHBoxLayout()
            line.setSpacing(6)
            label = QLabel(text)
            label.setObjectName('quillHintText')
            self.text_lines.append(label)
            line.addWidget(label)
            line.addWidget(button)
            line.addStretch(1)
            lines.addLayout(line)
        self.quill = QLabel()
        self.quill.setProperty('quill', True)  # she hides the hub's scales
        picture = trimmed(quill.pixmap(name, PICTURE))
        if not picture.isNull():
            self.quill.setPixmap(picture)
            self.quill.setFixedSize(picture.deviceIndependentSize().toSize())
        if self.side == 'left':  # she is in the left corner, the bubble to the right
            row.addWidget(self.quill, 0, Qt.AlignmentFlag.AlignBottom)
            row.addWidget(self.bubble, 0, Qt.AlignmentFlag.AlignTop)
        else:
            row.addWidget(self.bubble, 0, Qt.AlignmentFlag.AlignTop)
            row.addWidget(self.quill, 0, Qt.AlignmentFlag.AlignBottom)
        self.set_dark(False)
        self.adjustSize()
        self.hide()

    def _button(self, glyph, tip, callback):
        button = QToolButton()
        button.setIcon(icon(glyph))
        button.setIconSize(QSize(20, 20))
        button.setFixedSize(30, 30)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.setToolTip(tip)
        button.setAccessibleName(tip)
        button.clicked.connect(callback)
        return button

    def _edit(self):
        self.on_edit()  # she stays until the molecule appears (Compass calls dismiss then)

    def _open(self):
        self.on_open()  # an open cancelled leaves her where she is

    def dismiss(self):
        """Gone until the program is started again (the flag lives only in this run); the field shows its pale hint."""
        self.dismissed = True
        self.hide()
        field = self.parentWidget()
        for child in field.findChildren(QWidget) if field is not None else ():
            if hasattr(child, 'hint_shown'):
                child.hint_shown = False
                child.update()

    def set_dark(self, dark):
        # Compass calls this at every resize of the field — the styles are set only when the theme has changed
        if getattr(self, '_dark', None) is bool(dark):
            return
        self._dark = bool(dark)
        self.bubble.set_colors('#1c2a42' if dark else '#ffffff', '#2a3c5c' if dark else '#d8dce3')
        ink = '#c9d1dc' if dark else '#3b4657'
        hover = '#2a3c5c' if dark else '#eef2f7'
        for label in self.text_lines:
            label.setStyleSheet(f'color: {ink}; font-size: 14px; background: transparent;')
        for button in (self.edit_button, self.open_button):
            button.setStyleSheet(
                f'QToolButton {{border: 1px solid transparent; border-radius: 7px; background: transparent;}}'
                f'QToolButton:hover {{background: {hover}; border-color: {"#6ea2f0" if dark else "#2a62b8"};}}'
            )

    def fits(self, field):
        return field.width() >= self.width() + 2 * MARGIN and field.height() >= self.height() + 2 * MARGIN

    def place(self, field):
        self.adjustSize()
        if not self.fits(field):
            return False
        x = field.left() + MARGIN if self.side == 'left' else field.right() - self.width() - MARGIN
        self.move(x, field.bottom() - self.height() - MARGIN)
        self.raise_()
        return True
