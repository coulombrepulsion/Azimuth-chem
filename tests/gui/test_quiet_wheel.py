"""A combo box keeps its value under the wheel; the chosen section of the side panel is a see-through
tint (as --rail-on of site/rail.js), in both themes."""

import re

from PySide6.QtCore import QPoint, QPointF, Qt
from PySide6.QtGui import QWheelEvent
from PySide6.QtWidgets import QComboBox, QStyle

from tests.gui_support import *  # noqa: F401,F403 — the fixtures app, window and the helpers


def _wheel(widget, dy):
    return QWheelEvent(QPointF(5, 5), QPointF(widget.mapToGlobal(QPoint(5, 5))), QPoint(0, 0), QPoint(0, dy),
                       Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier, Qt.ScrollPhase.NoScrollPhase, False)


def test_the_wheel_does_not_turn_a_combo_box(app):
    from azimuth import app as azimuth_app

    azimuth_app.use_fusion(app)
    assert app.style().styleHint(QStyle.StyleHint.SH_ComboBox_AllowWheelScrolling) == 0
    combo = QComboBox()
    combo.addItems(['один', 'два', 'три', 'четыре'])
    combo.setCurrentIndex(1)
    combo.show()
    combo.setFocus()  # even with the focus
    for dy in (-120, 120, -360):
        app.sendEvent(combo, _wheel(combo, dy))
    assert combo.currentIndex() == 1
    combo.close()


def test_the_chosen_section_is_a_see_through_tint():
    from azimuth import app as azimuth_app

    for sheet, alpha in ((azimuth_app.STYLE, '42, 98, 184'), (azimuth_app.DARK_STYLE, '110, 162, 240')):
        checked = re.search(r'QPushButton#nav:checked \{background: ([^;]+);', sheet).group(1)
        hover = re.search(r'QPushButton#nav:hover:!checked \{background: ([^;]+);', sheet).group(1)
        for colour in (checked, hover):
            parts = re.fullmatch(r'rgba\((\d+), (\d+), (\d+), (\d+)\)', colour)
            assert parts and colour.startswith('rgba(' + alpha) and int(parts.group(4)) < 80, colour
