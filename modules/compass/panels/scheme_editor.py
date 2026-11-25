"""«Отображение → Свой вид…»: one window to make the look of the model one's own and keep it as a scheme.

§1 PURPOSE
    Instead of the many ready looks of Chemcraft's «Отображение», the user makes their own: every parameter of a
    display scheme (modules/compass/view/schemes.py) in one window, the model following each change at once; the colour
    of any element; the result kept under a name (the list of «Схема отображения»), sent to a colleague as a
    file and read back, or made the look the program starts with.
§2 ALGORITHM The window starts from the current look (owner.scheme_tool.current_scheme()) and remembers it: «Вернуть как
    было» puts it back. A change of a field makes the scheme anew from all the fields and applies it
    (owner.scheme_tool.apply_scheme) — the same path as the menus, so the preferences are written as before. The files
    of «Экспорт…» / «Импорт…» are those of schemes.dump / schemes.parse (version 1, several schemes in one file); an
    imported name that is taken gets « (2)».
§4 SPECIFICATION
    SchemeEditor(owner) — owner: CompassWorkspace (current_scheme, apply_scheme, user_schemes, save_scheme,
    set_start_scheme, preferences). Fields: mode, atom_scale, bond_width, bond_color, show_bonds, multiple_bonds,
    palette, background, grid, label_mode, perspective, show_axes; element (QComboBox of symbols), element_button,
    colors_list (QListWidget of own colours); name (QLineEdit), save_button, start_box. scheme() -> dict;
    set_color(symbol, '#rrggbb' | None) — None removes the own colour; save(name=None) -> name | None;
    export(path, names=None) -> number; import_file(path) -> [names]; revert().
§7 TESTS
    tests/test_gui.py::test_own_display_scheme.
"""

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout,
                               QGroupBox, QHBoxLayout, QLineEdit, QListWidget, QListWidgetItem, QVBoxLayout)

from azimuth.core import SYMBOLS
from azimuth.i18n import tr
from azimuth.ui import button, label
from modules.compass.view import schemes

MODES = (('ball-stick', 'Шары и стержни'), ('sticks', 'Стержни'), ('spacefill', 'Объёмная модель'))
BOND_COLORS = (('smooth', 'По атомам · плавный переход'), ('split', 'По атомам · чёткая граница'),
               ('uniform', 'Одноцветные'))
PALETTES = (('azimuth', 'Азимут'), ('jmol', 'Jmol (CPK)'), ('mono', 'Оттенки серого'))
BACKGROUNDS = (('theme', 'Как тема'), ('white', 'Белый'), ('black', 'Чёрный'))
LABELS = (('element', 'Элемент · C'), ('number', 'Номер · 1'), ('both', 'Элемент и номер · C1'),
          ('group', 'Номер в элементе · C1, H1'), ('none', 'Без подписей'))
FILTER = 'Схемы Азимута (*.json)'


def _combo(options, value):
    box = QComboBox()
    for key, title in options:
        box.addItem(tr(title), key)
    box.setCurrentIndex(max(0, box.findData(value)))
    return box


def _swatch(color):
    pixmap = QPixmap(14, 14)
    pixmap.fill(QColor(color))
    return QIcon(pixmap)


class SchemeEditor(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(tr('Свой вид'))
        self.setObjectName('schemeEditor')
        self.start = owner.scheme_tool.current_scheme()
        self.colors = dict(self.start['colors'])
        s = self.start
        outer = QVBoxLayout(self)
        note = label(tr('Каждое изменение сразу видно на модели. Получившийся вид можно сохранить как схему — она '
                        'появится в «Схеме отображения», — отправить файлом или выбрать для запуска программы.'),
                     'subtitle')
        note.setWordWrap(True)
        outer.addWidget(note)
        row = QHBoxLayout()
        left, right = QVBoxLayout(), QVBoxLayout()
        row.addLayout(left, 1)
        row.addLayout(right, 1)
        outer.addLayout(row)

        model = QGroupBox(tr('Модель'))
        form = QFormLayout(model)
        self.mode = _combo(MODES, s['display_mode'])
        form.addRow(tr('Вид'), self.mode)
        self.atom_scale = self._number(0.4, 2.5, 0.05, s['atom_scale'], ' ×')
        form.addRow(tr('Размер атомов'), self.atom_scale)
        self.label_mode = _combo(LABELS, s['label_mode'])
        form.addRow(tr('Подписи'), self.label_mode)
        self.perspective = QCheckBox(tr('Перспектива'))
        self.perspective.setChecked(s['perspective'])
        self.show_axes = QCheckBox(tr('Оси X, Y, Z'))
        self.show_axes.setChecked(s['show_axes'])
        form.addRow(self.perspective)
        form.addRow(self.show_axes)
        left.addWidget(model)

        bonds = QGroupBox(tr('Связи'))
        form = QFormLayout(bonds)
        self.bond_width = self._number(0.3, 3.0, 0.1, s['bond_width'], ' ×')
        form.addRow(tr('Толщина'), self.bond_width)
        self.bond_color = _combo(BOND_COLORS, s['bond_color'])
        form.addRow(tr('Цвет'), self.bond_color)
        self.show_bonds = QCheckBox(tr('Показывать связи'))
        self.show_bonds.setChecked(s['show_bonds'])
        self.multiple_bonds = QCheckBox(tr('Показывать двойные и тройные связи'))
        self.multiple_bonds.setChecked(s['multiple_bonds'])
        form.addRow(self.show_bonds)
        form.addRow(self.multiple_bonds)
        left.addWidget(bonds)

        field = QGroupBox(tr('Поле'))
        form = QFormLayout(field)
        self.background = _combo(BACKGROUNDS, s['background'])
        form.addRow(tr('Фон'), self.background)
        self.grid = QCheckBox(tr('Сетка точек'))
        self.grid.setChecked(s['grid'])
        form.addRow(self.grid)
        left.addWidget(field)
        left.addStretch(1)

        colours = QGroupBox(tr('Цвета элементов'))
        form = QFormLayout(colours)
        self.palette = _combo(PALETTES, s['palette'])
        form.addRow(tr('Основа'), self.palette)
        self.element = QComboBox()
        present = sorted({a.symbol for a in owner.molecule.atoms if a.symbol != 'X'},
                         key=SYMBOLS.index) if owner.molecule else []
        for symbol in present + [x for x in SYMBOLS if x not in present and x != 'X']:
            self.element.addItem(symbol, symbol)
        self.element_button = button(tr('Свой цвет…'), self.choose_color)
        pick = QHBoxLayout()
        pick.addWidget(self.element, 1)
        pick.addWidget(self.element_button)
        form.addRow(tr('Элемент'), pick)
        self.colors_list = QListWidget()
        self.colors_list.setMaximumHeight(120)
        self.colors_list.setToolTip(tr('Свои цвета элементов поверх основы; двойной щелчок убирает цвет'))
        self.colors_list.itemDoubleClicked.connect(lambda item: self.set_color(item.data(Qt.ItemDataRole.UserRole),
                                                                               None))
        form.addRow(self.colors_list)
        right.addWidget(colours)

        keep = QGroupBox(tr('Схема'))
        form = QFormLayout(keep)
        self.name = QLineEdit()
        self.name.setPlaceholderText(tr('Название, например «Для статьи»'))
        self.save_button = button(tr('Сохранить схему'), lambda: self.save())
        line = QHBoxLayout()
        line.addWidget(self.name, 1)
        line.addWidget(self.save_button)
        form.addRow(line)
        self.start_box = QCheckBox(tr('Открывать программу с этой схемой'))
        form.addRow(self.start_box)
        files = QHBoxLayout()
        files.addWidget(button(tr('Экспорт схем…'), lambda: self.export()))
        files.addWidget(button(tr('Импорт схем…'), lambda: self.import_file()))
        form.addRow(files)
        right.addWidget(keep)
        right.addStretch(1)

        bottom = QHBoxLayout()
        bottom.addWidget(button(tr('Вернуть как было'), self.revert))
        bottom.addStretch(1)
        bottom.addWidget(button(tr('Закрыть'), self.accept))  # what closes is white
        outer.addLayout(bottom)

        for combo in (self.mode, self.label_mode, self.bond_color, self.background, self.palette):
            combo.currentIndexChanged.connect(self.apply)
        for box in (self.perspective, self.show_axes, self.show_bonds, self.multiple_bonds, self.grid):
            box.toggled.connect(self.apply)
        for spin in (self.atom_scale, self.bond_width):
            spin.valueChanged.connect(self.apply)
        self._show_colors()

    @staticmethod
    def _number(low, high, step, value, suffix):
        spin = QDoubleSpinBox()
        spin.setRange(low, high)
        spin.setSingleStep(step)
        spin.setDecimals(2)
        spin.setSuffix(suffix)
        spin.setValue(value)
        return spin

    # -- the scheme of the fields ------------------------------------------------------------------------------------
    def scheme(self):
        return schemes.normalize({
            'display_mode': self.mode.currentData(), 'bond_color': self.bond_color.currentData(),
            'bond_width': self.bond_width.value(), 'show_bonds': self.show_bonds.isChecked(),
            'multiple_bonds': self.multiple_bonds.isChecked(), 'label_mode': self.label_mode.currentData(),
            'perspective': self.perspective.isChecked(), 'show_axes': self.show_axes.isChecked(),
            'atom_scale': self.atom_scale.value(), 'palette': self.palette.currentData(), 'colors': dict(self.colors),
            'background': self.background.currentData(), 'grid': self.grid.isChecked()})

    def apply(self, *args):
        self.owner.scheme_tool.apply_scheme(self.scheme())
        return self.scheme()

    def _fill(self, s):
        """The fields show the scheme s (without applying it field by field)."""
        widgets = (self.mode, self.label_mode, self.bond_color, self.background, self.palette, self.perspective,
                   self.show_axes, self.show_bonds, self.multiple_bonds, self.grid, self.atom_scale, self.bond_width)
        for w in widgets:
            w.blockSignals(True)
        for combo, key in ((self.mode, 'display_mode'), (self.label_mode, 'label_mode'), (self.bond_color, 'bond_color'),
                           (self.background, 'background'), (self.palette, 'palette')):
            combo.setCurrentIndex(max(0, combo.findData(s[key])))
        for box, key in ((self.perspective, 'perspective'), (self.show_axes, 'show_axes'),
                         (self.show_bonds, 'show_bonds'), (self.multiple_bonds, 'multiple_bonds'), (self.grid, 'grid')):
            box.setChecked(s[key])
        self.atom_scale.setValue(s['atom_scale'])
        self.bond_width.setValue(s['bond_width'])
        for w in widgets:
            w.blockSignals(False)
        self.colors = dict(s['colors'])
        self._show_colors()

    def revert(self):
        self._fill(self.start)
        self.owner.scheme_tool.apply_scheme(self.start)
        return self.start

    # -- colours of elements -------------------------------------------------------------------------------------
    def choose_color(self):
        symbol = self.element.currentData()
        now = schemes.palette(self.scheme()).get(symbol, schemes.NEUTRAL)
        from modules.compass.actions.style_form import pick_colour

        chosen = pick_colour(now, self, tr('Цвет элемента ') + symbol)  # one compact picker everywhere
        if chosen:
            return self.set_color(symbol, chosen)
        return None

    def set_color(self, symbol, color):
        if color is None:
            self.colors.pop(symbol, None)
        else:
            self.colors[symbol] = QColor(color).name()
        self._show_colors()
        self.apply()
        return dict(self.colors)

    def _show_colors(self):
        self.colors_list.clear()
        for symbol in sorted(self.colors, key=SYMBOLS.index):
            item = QListWidgetItem(_swatch(self.colors[symbol]), f'{symbol}  {self.colors[symbol]}')
            item.setData(Qt.ItemDataRole.UserRole, symbol)
            self.colors_list.addItem(item)
        if not self.colors:
            item = QListWidgetItem(tr('Своих цветов нет — все из основы'))
            item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.colors_list.addItem(item)

    # -- keeping, files ------------------------------------------------------------------------------------------
    def save(self, name=None):
        self.apply()
        name = self.owner.scheme_tool.save_scheme(name if name is not None else self.name.text())
        if name and self.start_box.isChecked():
            self.owner.scheme_tool.set_start_scheme(name)
        return name

    def export(self, path=None, names=None):
        """The own schemes (names: some of them; none — all, and the current look as «Свой вид» if there are none)."""
        chosen = {n: s for n, s in self.owner.user_schemes.items() if names is None or n in names}
        if not chosen:
            chosen = {tr('Свой вид'): self.scheme()}
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, tr('Экспорт схем'), 'Azimuth-schemes.json', tr(FILTER))
            if not path:
                return None
        Path(path).write_text(schemes.dump(chosen), encoding='utf-8')
        return len(chosen)

    def import_file(self, path=None):
        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, tr('Импорт схем'), '', tr(FILTER))
            if not path:
                return None
        try:
            found = schemes.parse(Path(path).read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            self.owner.error(exc)
            return None
        taken = []
        for name, scheme in found.items():
            new, k = name, 2
            while new in self.owner.user_schemes or new in schemes.BUILTIN:
                new, k = f'{name} ({k})', k + 1
            self.owner.user_schemes[new] = scheme
            taken.append(new)
        from modules.compass.actions.scheme_actions import SETTINGS_KEY

        self.owner.preferences.setValue(SETTINGS_KEY, schemes.dump(self.owner.user_schemes))
        if taken:
            self.owner.scheme_tool.apply_scheme(found[next(iter(found))])
            self._fill(self.owner.scheme_tool.current_scheme())
        self.owner.notify(tr('Схем добавлено: ') + str(len(taken)) + ' — ' + ', '.join(taken), 8000)
        return taken
