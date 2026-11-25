"""Small parts of the page of Compass: a widget that matches the height of another (_MatchHeight), the Delete key
of the field (DeleteKey), the box whose width slides for the side panel (side_slide_box), the pill of the chosen
fragment or molecule that opens their menu again (ChoicePill).

Split off modules/compass/panels/layout.py (0.222.30).
"""

from PySide6.QtCore import QEvent, QObject, QSize, Qt
from PySide6.QtWidgets import QAbstractItemView, QLabel


class _MatchHeight(QObject):
    """The button ☰ as tall as the tabs «Молекула | Координаты» next to it (square), whatever the style sheet."""

    def __init__(self, source, target):
        super().__init__(source)
        self.target = target
        source.installEventFilter(self)

    def eventFilter(self, watched, event):
        if event.type() == QEvent.Type.Resize:
            side = max(20, watched.height() - 2)
            if self.target.height() != side:
                self.target.setFixedSize(side, side)
                self.target.setIconSize(QSize(side - 8, side - 8))
        return False


class DeleteKey(QObject):
    """Delete (Windows, Linux) or Backspace (Mac) in the coordinates table removes the atoms of the selected
    rows, as on the model; while a cell is being edited the key belongs to the cell."""

    def __init__(self, table, callback):
        super().__init__(table)
        self.callback = callback
        table.installEventFilter(self)

    def eventFilter(self, watched, event):
        if (event.type() == QEvent.Type.KeyPress and event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace)
                and watched.state() != QAbstractItemView.State.EditingState and watched.selectedIndexes()):
            self.callback()
            return True
        return False


def side_slide_box(child):
    """A box of width 0…that of child (child.slide_width, set by CrystalTool.slide_side) — the child keeps
    its width at the left edge of the box, the field beside it gives way at the pace of the box; hidden while folded."""
    from PySide6.QtWidgets import QWidget

    class SideSlideBox(QWidget):
        def resizeEvent(self, event):
            super().resizeEvent(event)
            self.place()

        def place(self):
            width = getattr(child, 'slide_width', 0) or child.width()
            for item in self.children():
                if isinstance(item, QWidget):
                    item.setGeometry(0, 0, width, self.height())

    box = SideSlideBox()
    box.setObjectName('crystalSideSlide')
    child.setParent(box)
    box.setFixedWidth(0)
    box.hide()
    return box


class ChoicePill(QLabel):
    """The name of the chosen fragment or molecule next to its button; a click on it opens their menu again to choose
    another (the owner, 2026-11-24: «нажимать на отдельное поле, где название, чтобы выбрать другой»)."""

    def __init__(self, on_click, parent=None):
        super().__init__('', parent)
        self.setObjectName('choicePill')
        self.setWordWrap(True)
        self.on_click = on_click
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.on_click is not None:
            event.accept()
            self.on_click()
            return
        super().mousePressEvent(event)
