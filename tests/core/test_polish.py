"""azimuth/polish.py: centred table cells and the smooth appearance of dialogs."""

import os

import pytest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
pytest.importorskip('PySide6')

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtGui import QStandardItem, QStandardItemModel  # noqa: E402
from PySide6.QtWidgets import QApplication, QStyledItemDelegate, QStyleOptionViewItem, QTableView  # noqa: E402

from azimuth import polish  # noqa: E402


@pytest.fixture(scope='module')
def app():
    return QApplication.instance() or QApplication([])


def test_animations_switched_off_in_tests_and_by_variable():
    assert not polish.animations_allowed({'QT_QPA_PLATFORM': 'offscreen'})
    assert not polish.animations_allowed({'AZIMUTH_NO_ANIMATION': '1'}, 'cocoa')
    assert polish.animations_allowed({}, 'cocoa')


def test_macos_sheets_are_left_to_the_system():
    assert polish.is_sheet(Qt.WindowModality.WindowModal, 'darwin')
    assert not polish.is_sheet(Qt.WindowModality.ApplicationModal, 'darwin')
    assert not polish.is_sheet(Qt.WindowModality.WindowModal, 'win32')


def test_tables_are_centred_and_own_delegates_kept(app):
    polish.install(app)
    assert polish.install(app) is polish.install(app)  # one filter, however often it is installed
    model = QStandardItemModel(1, 1)
    item = QStandardItem('1,23')
    item.setTextAlignment(Qt.AlignmentFlag.AlignRight)
    model.setItem(0, 0, item)
    view = QTableView()
    view.setModel(model)
    view.show()
    app.processEvents()
    assert isinstance(view.itemDelegate(), polish.CenterDelegate)
    view.close()
    assert polish.uninstall(app) and not polish.uninstall(app)  # taken off, once
    assert view.horizontalHeader().defaultAlignment() == Qt.AlignmentFlag.AlignCenter
    option = QStyleOptionViewItem()
    view.itemDelegate().initStyleOption(option, model.index(0, 0))
    assert option.displayAlignment == Qt.AlignmentFlag.AlignCenter
    own = QTableView()

    class Mine(QStyledItemDelegate):
        pass

    mine = Mine(own)
    own.setItemDelegate(mine)
    own.setModel(model)
    own.show()
    app.processEvents()
    assert own.itemDelegate() is mine
    view.close()
    own.close()


def test_tooltips_only_where_they_tell_something(app):
    """No tooltip of a frame over its empty places, none repeating the words shown; the icon without
    words and the field explaining its setting keep theirs."""
    from PySide6.QtCore import QEvent, QPoint
    from PySide6.QtGui import QHelpEvent
    from PySide6.QtWidgets import QDoubleSpinBox, QFrame, QLabel, QPushButton, QVBoxLayout, QWidget

    event = QHelpEvent(QEvent.Type.ToolTip, QPoint(1, 1), QPoint(1, 1))
    panel = QWidget()
    panel.setToolTip('Панель всего')
    column = QVBoxLayout(panel)
    child = QPushButton('Показать')
    column.addWidget(child)
    assert not polish.tooltip_wanted(panel, event, under=panel)  # its own empty place
    assert not polish.tooltip_wanted(panel, event, under=child)  # passed up from a child without one
    child.setToolTip('Показать')
    assert not polish.tooltip_wanted(child, event, under=child)  # the words of the button again
    child.setToolTip('Выбранная орбиталь на модели · двойной щелчок по строке')
    assert polish.tooltip_wanted(child, event, under=child)
    icon = QPushButton()
    icon.setToolTip('Копировать таблицу')
    assert polish.tooltip_wanted(icon, event, under=icon)
    from azimuth.controls import ExpandingButton

    folded = ExpandingButton('Остановить', None, 'stop')  # its words only in its tooltip while it is folded
    assert polish.tooltip_wanted(folded, event, under=folded)
    folded.unfolded = True
    assert not polish.tooltip_wanted(folded, event, under=folded)
    frame = QFrame()
    frame.setToolTip('Рамка')
    assert not polish.tooltip_wanted(frame, event, under=frame)
    label = QLabel('Электронная плотность')
    label.setToolTip('Электронная плотность')
    assert not polish.tooltip_wanted(label, event, under=label)
    label.setToolTip('Длинное объяснение того, что это за плотность')
    assert polish.tooltip_wanted(label, event, under=label)
    spin = QDoubleSpinBox()
    spin.setToolTip('Температура больцмановских долей')
    assert polish.tooltip_wanted(spin, event, under=spin.lineEdit())  # the field of the setting keeps its explanation


def test_the_values_of_the_fields_are_in_their_middle(app):
    """."""
    from PySide6.QtWidgets import QDoubleSpinBox, QFileDialog, QLineEdit

    spin, line = QDoubleSpinBox(), QLineEdit()
    assert polish.center_field(spin) and spin.alignment() & Qt.AlignmentFlag.AlignHCenter
    assert polish.center_field(line) and line.alignment() & Qt.AlignmentFlag.AlignHCenter
    assert not polish.center_field(spin.lineEdit())  # the spin box sets its own line
    kept = QLineEdit()
    kept.setProperty('azimuthKeepAlignment', True)
    assert not polish.center_field(kept)
    dialog = QFileDialog()
    path = QLineEdit(dialog)
    assert not polish.center_field(path)


def test_the_name_of_a_row_of_a_form_ends_with_a_colon():
    import pytest

    pytest.importorskip('PySide6')
    from PySide6.QtWidgets import QApplication, QCheckBox, QFormLayout, QLabel, QLineEdit, QWidget

    app = QApplication.instance() or QApplication([])
    holder = QWidget()
    form = QFormLayout(holder)
    form.addRow('Толщина', QLineEdit())
    form.addRow(QLabel('Длина:'), QLineEdit())
    form.addRow(QLabel('Что это?'), QLineEdit())
    form.addRow('', QCheckBox('показывать'))
    changed = polish.colon_labels(holder)
    texts = [form.itemAt(k, QFormLayout.ItemRole.LabelRole).widget().text() for k in range(3)]
    assert texts == ['Толщина:', 'Длина:', 'Что это?'] and len(changed) == 1
    assert polish.colon_labels(holder) == []  # once
    holder.deleteLater()
    assert app is not None


def test_the_small_windows_come_back_over_the_main_window():
    # «если поверх открывают другую программу, то малые окна по типу настроек уходят на задний план»: when the program
    # is in front again, the windows with an owner are raised — not the main window, a menu, a tooltip or a hidden one
    from PySide6.QtCore import Qt

    from azimuth import polish

    class Window:
        def __init__(self, owner=True, shown=True, minimized=False, kind=Qt.WindowType.Window):
            self.owner, self.shown, self.minimized, self.kind = owner, shown, minimized, kind

        def isWindow(self):
            return True

        def isVisible(self):
            return self.shown

        def isMinimized(self):
            return self.minimized

        def parentWidget(self):
            return object() if self.owner else None

        def windowType(self):
            return self.kind

    settings, main, hidden = Window(), Window(owner=False), Window(shown=False)
    tooltip, folded = Window(kind=Qt.WindowType.ToolTip), Window(minimized=True)
    assert polish.owned_windows([main, settings, hidden, tooltip, folded]) == [settings]


def test_the_choice_of_a_combo_box_is_centred(app):
    # «центрируй в полях все»: a combo box draws its choice in the middle, as a spin box its number; an editable one and
    # one that asks to stay as it is are left
    from PySide6.QtWidgets import QComboBox

    plain, editable, kept = QComboBox(), QComboBox(), QComboBox()
    editable.setEditable(True)
    kept.setProperty('azimuthKeepAlignment', True)
    assert polish.center_choice(plain) and plain.property('quail_center')
    assert not polish.center_choice(editable) and not polish.center_choice(kept) and not kept.property('quail_center')


def test_a_long_plain_tooltip_is_folded_into_lines():
    # Windows of the owner (2026-11-24): a plain tooltip is one line as wide as the screen («Окружение для»)
    from azimuth.polish import TIP_LINE, wrapped_tip

    long = 'Чьи строки показаны ниже: «Все программы» — попадают в каждую задачу этого сервера; строки программы — ' \
           'только в её задачи, после общих.'
    assert len(long) > TIP_LINE and wrapped_tip(long).startswith('<p>') and '«Все программы»' in wrapped_tip(long)
    assert wrapped_tip('Короткая подсказка') is None and wrapped_tip('<b>уже</b> ' + long) is None
    assert wrapped_tip('a < b ' + 'x' * 90).count('&lt;') == 1  # the text escaped, not read as markup
