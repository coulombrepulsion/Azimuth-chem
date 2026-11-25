"""The menu bar of Azimuth: «Файл», «Правка», «Вид», «Структура», «Расчёт», «Анализ», «Справка» and their items.
build_menus is a method of Studio (self is the window), kept here to make app.py shorter.

Split off azimuth/app.py (0.222.30).
"""

import sys
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QActionGroup, QShortcut, QKeySequence
from .core import EXAMPLES
from .icons import icon
from .ui import smooth
from azimuth.i18n import tr


def build_menus(self):
    bar = self.menuBar()
    bar.setNativeMenuBar(False)

    def action(menu, title, callback, shortcut=None):
        item = QAction(title, self)
        item.triggered.connect(callback)
        if shortcut:
            item.setShortcut(shortcut)
        menu.addAction(item)
        return item

    files = bar.addMenu(tr('Файл'))
    action(files, tr('Новая молекула'), self.new_molecule_command, QKeySequence.StandardKey.New)
    self.open_action = action(files, tr('Открыть…'), self.opening_tool.open_any, QKeySequence.StandardKey.Open)
    self.open_action.setIcon(icon('folder'))  # the folder the hint of the empty field points to
    # files of the heavy atoms only (databases) get their hydrogens when opened
    self.hydrogens_open_action = action(files, tr('Достраивать водороды у файлов без H'), lambda *a: None)
    self.hydrogens_open_action.setCheckable(True)
    self.hydrogens_open_action.setChecked(self.opening_tool.hydrogens_on_open())
    self.hydrogens_open_action.setToolTip(tr('Если в открытом файле нет ни одного атома H, они достраиваются по '
                                             'валентности (C 4, N 3, O 2…); файл с водородами не меняется'))
    self.hydrogens_open_action.toggled.connect(lambda on: self.preferences.setValue(self.HYDROGENS_ON_OPEN, bool(on)))
    files.setToolTipsVisible(True)
    # the files opened last and Ctrl+R (as in Chemcraft)
    self.recent_menu = smooth(files.addMenu(tr('Недавние файлы')))
    self.recent_menu.setToolTipsVisible(True)
    self.recent_menu.aboutToShow.connect(lambda: self.file_tool.fill_recent_menu(self.recent_menu))
    self.reload_action = action(files, tr('Перечитать файл'), self.file_tool.reload_file, 'Ctrl+R')
    self.reload_action.setToolTip(tr('Прочитать заново файл этой вкладки — например, вывод расчёта, который ещё идёт'))
    action(files, tr('Открыть пример…'), self.opening_tool.open_example)  # examples/
    action(files, tr('Открыть проект…'), self.open_project)
    action(files, tr('Новый проект с расчётами…'), lambda: self.new_project_tab())
    action(files, tr('Создать проект из расчётов…'), lambda: self.project_from_calculations())
    action(files, tr('Молекулы и расчёты проекта…'), self.show_research_project)
    action(files, tr('Молекула по SMILES…'), self.opening_tool.molecule_from_smiles)
    # «Файл» — a name of PubChem, the clipboard, saving without a question, the tabs, the file of the tab
    action(files, tr('Молекула по названию…'), lambda: self.file_tool.molecule_by_name())
    action(files, tr('Вставить структуру из буфера'), lambda: self.file_tool.paste_structure(), 'Ctrl+Shift+V')
    action(files, tr('Сохранить'), self.save_project, QKeySequence.StandardKey.Save)
    action(files, tr('Сохранить как…'), self.save_project_as, 'Ctrl+Shift+S')
    action(files, tr('Восстановить аварийные копии…'), lambda: self.recovery.recover())
    action(files, tr('Закрыть вкладку'), self.file_tool.close_current_tab, 'Ctrl+W')
    action(files, tr('Закрыть остальные вкладки'), self.file_tool.close_other_tabs)
    action(files, tr('Очистить'), self.file_tool.clear_tab)
    action(files, tr('Показать файл в папке'), self.file_tool.reveal_file)
    files.addSeparator()
    action(files, tr('Открыть XYZ…'), self.opening_tool.open_xyz)
    action(files, tr('Открыть CUBE (3D)…'), self.open_cube)
    action(files, tr('Открыть орбитали…'), self.open_orbitals)
    action(files, tr('Учебная орбиталь (3D)'), self.demo_cube)
    action(files, tr('Сохранить XYZ (Å)…'), self.opening_tool.export_xyz)
    action(files, tr('Сохранить координаты в выбранном формате…'), self.coordinate_tool.save_coordinates)
    self.batch_menu = self.file_tool.build_batch_menu()  # many structures at once
    files.addMenu(self.batch_menu)
    action(files, tr('Сохранить входной файл ORCA…'), self.input_tool.export_input)
    action(files, tr('Открыть результат расчёта…'), self.open_result_file)
    action(files, tr('Диаграмма реакции…'), self.reaction_diagram)
    action(files, tr('Шаги оптимизации…'), self.trajectory_tool.open_trajectory)
    action(files, tr('Наложить структуру для сравнения…'), self.overlay_tool.open_compare)
    examples = files.addMenu(tr('Примеры молекул'))
    for name in EXAMPLES:
        action(examples, name, lambda checked=False, n=name: self.opening_tool.load_example_menu(n))
    examples.addSeparator()
    from modules.compass.chemistry import library  # the grouped library

    for title, names in library.MOLECULE_GROUPS.items():
        group = examples.addMenu(tr(title))
        for name in names:
            action(group, tr(name), lambda checked=False, n=name: self.opening_tool.load_example_menu(n))
    examples.addSeparator()  # the user's own molecules, made anew each time the menu opens
    self.user_molecules_menu = examples.addMenu(tr('Мои молекулы'))
    self.user_molecules_menu.aboutToShow.connect(
        lambda: self.fragment_tool.fill_user_molecules_menu(self.user_molecules_menu))
    action(files, tr('Учебный результат ORCA'), self.demo_output)
    action(files, tr('Учебная оптимизация ORCA'), self.opening_tool.demo_optimization)
    action(files, tr('Учебные колебания ORCA'), self.demo_vibrations)
    files.addSeparator()
    self.settings_action = action(files, tr('Настройки…'), lambda: self.show_settings())
    self.settings_action.setMenuRole(QAction.MenuRole.NoRole)
    # the logs, the versions and the settings (no passwords) in one .zip for the author
    self.report_action = action(files, tr('Отчёт об ошибке…'), lambda: self.save_error_report())
    self.exit_action = action(files, tr('Выход'), self.close)
    edit = bar.addMenu(tr('Правка'))
    edit.setToolTipsVisible(True)
    self.undo_action = action(edit, tr('Отменить'), self.undo_geometry)
    self.undo_action.setToolTip(tr('Отменить изменение · Ctrl+Z / Cmd+Z'))
    self.redo_action = action(edit, tr('Повторить'), self.redo_geometry)
    self.redo_action.setToolTip(tr('Повторить изменение · Ctrl+Shift+Z / Cmd+Shift+Z'))
    self.connect_action = action(edit, tr('Создать связь'), self.apply_bond)
    self.connect_action.setToolTip(tr('Выделите два атома. Ctrl+B / Cmd+B переключает наличие связи.'))
    self.disconnect_action = action(edit, tr('Разорвать связь'), lambda: self.apply_bond(remove=True))
    self.disconnect_action.setToolTip(tr('Выделите два атома. Ctrl+B / Cmd+B переключает наличие связи.'))
    action(edit, tr('Добавить атом…'), self.add_atom)
    action(edit, tr('Добавить фрагмент'), lambda: self.select_mode(2))
    action(edit, tr('Добавить молекулу'), self.add_molecule)
    action(edit, tr('Сохранить выделенное как фрагмент…'), lambda: self.fragment_tool.save_selection_as_fragment())
    action(edit, tr('Сохранить молекулу в «Мои молекулы»…'), lambda: self.fragment_tool.save_molecule())
    action(edit, tr('Вращать вокруг связи…'), lambda: self.compass_dialogs.torsion())
    action(edit, tr('Редактор Z-матрицы…'), lambda: self.view_tool.open_zmatrix_editor())
    action(edit, tr('Путь между структурами…'), lambda: self.compass_dialogs.path())
    self.conformers_action = action(edit, tr('Поиск конформеров…'), lambda: self.compass_dialogs.conformers())
    action(edit, tr('Обзор / выделение'), lambda: self.select_mode(0))
    action(edit, tr('Связать / разорвать (Ctrl+B; на Mac также Cmd+B)'), self.toggle_bond)
    action(edit, tr('Удалить выбранные атомы (Delete)'), self.remove_atom)
    self.bond_shortcuts = []
    sequences = ['Ctrl+B'] + (['Meta+B'] if sys.platform == 'darwin' else [])
    for seq in sequences:
        shortcut = QShortcut(QKeySequence(seq), self.viewer)
        shortcut.setContext(Qt.ShortcutContext.WidgetShortcut)
        shortcut.activated.connect(self.toggle_bond)
        self.bond_shortcuts.append(shortcut)
    self.bond_button.setToolTip(
        tr('Связать два атома. Ctrl+B / Cmd+B переключает наличие связи (фокус на модели).')
    )
    self.unbond_button.setToolTip(tr('Удалить связь. Ctrl+B / Cmd+B переключает наличие связи.'))
    self.delete_button.setToolTip(tr('Delete / Backspace, когда фокус на модели'))
    for item, name in [
        (self.undo_action, 'undo'),
        (self.redo_action, 'redo'),
        (self.connect_action, 'connect'),
        (self.disconnect_action, 'disconnect'),
    ]:
        item.setIcon(icon(name))
    view = bar.addMenu(tr('Вид'))
    self.display_actions = {}
    display_group = QActionGroup(self)
    display_group.setExclusive(True)
    for i in range(self.display_mode.count()):
        key = self.display_mode.itemData(i)
        item = action(
            view, self.display_mode.itemText(i), lambda checked=False, n=i: self.display_mode.setCurrentIndex(n)
        )
        item.setCheckable(True)
        item.setChecked(key == self.viewer.display_mode)
        display_group.addAction(item)
        self.display_actions[key] = item
    view.addSeparator()
    bonds = view.addMenu(tr('Отображение связей'))
    view.addAction(self.lengths_action)
    view.addAction(self.hbonds_action)
    view.addMenu(self.properties_menu)

    def set_option(name, value):
        setattr(self.viewer, name, value)
        self.preferences.setValue(name, value)
        self.viewer.update()

    self.bond_color_actions = {}
    color_group = QActionGroup(self)
    color_group.setExclusive(True)
    color = self.preferences.value('bond_color', 'smooth')
    if color not in ('smooth', 'split', 'uniform'):
        color = 'smooth'
    self.viewer.bond_color = color
    for title, key in [
        (tr('По атомам · плавный переход'), 'smooth'),
        (tr('По атомам · чёткая граница'), 'split'),
        (tr('Одноцветные'), 'uniform'),
    ]:
        item = action(bonds, title, lambda checked=False, k=key: set_option('bond_color', k))
        item.setCheckable(True)
        item.setChecked(key == color)
        color_group.addAction(item)
        self.bond_color_actions[key] = item
    bonds.addSeparator()
    self.bond_option_actions = {}  # kept for the display schemes
    for title, key in [
        (tr('Показывать связи'), 'show_bonds'),
        (tr('Показывать двойные и тройные связи'), 'multiple_bonds'),
    ]:
        value = str(self.preferences.value(key, 'true')).lower() in ('true', '1')
        setattr(self.viewer, key, value)
        item = action(bonds, title, lambda checked, k=key: set_option(k, checked))
        item.setCheckable(True)
        item.setChecked(value)
        self.bond_option_actions[key] = item
    widths = bonds.addMenu(tr('Толщина'))
    width_group = QActionGroup(self)
    width_group.setExclusive(True)
    try:
        width = float(self.preferences.value('bond_width', 1.0))
    except (ValueError, TypeError):
        width = 1.0
    if not 0.3 <= width <= 3.0:  # any width of «Свой вид…» (the menu offers 0.6, 1.0, 1.6)
        width = 1.0
    self.viewer.bond_width = width
    self.bond_width_actions = {}
    for title, value in [(tr('Тонкие'), 0.6), (tr('Обычные'), 1.0), (tr('Толстые'), 1.6)]:
        item = action(widths, title, lambda checked=False, v=value: set_option('bond_width', v))
        item.setCheckable(True)
        item.setChecked(value == width)
        width_group.addAction(item)
        self.bond_width_actions[value] = item
    bonds.addSeparator()  # the colour, the width, the types of the bonds, the hydrogen bonds
    action(bonds, tr('Стиль связей…'), lambda: self.structure_tool.bond_style())
    view.addSeparator()
    view.addMenu(self.standard_view_menu)
    view.addMenu(self.surface_menu)
    if hasattr(self, 'compare_menu'):  # its button is gone from the row of Compass
        view.addMenu(self.compare_menu)
    view.addMenu(self.scheme_menu)  # display schemes
    # 2026-10-24; its name
    action(view, tr('Перестроить кристалл (ячейки, поверхность)…'), lambda: self.crystal_tool.reopen_crystal())
    action(view, tr('Сохранить кристалл в CIF…'), lambda: self.crystal_tool.save_crystal_cif())
    self.cell_action = action(view, tr('Показывать ячейку'), lambda checked: self.crystal_tool.set_cell_shown(checked))
    self.cell_action.setCheckable(True)
    self.cell_action.setChecked(True)
    # atoms and bonds drawn by VTK (OpenGL) — a trial next to the built-in renderer
    self.engine_action = action(view, tr('Трёхмерная графика VTK (проба)'), lambda checked: self.view_tool.set_engine(checked))
    self.engine_action.setCheckable(True)
    self.engine_action.setToolTip(tr('Атомы и связи рисует VTK; подписи, выделение и измерения — как прежде. Если VTK не заработает, Компас вернётся к встроенной графике.'))
    self.viewer.engineFailed.connect(self.view_tool.engine_failed)
    if str(self.preferences.value(self.ENGINE_KEY, 'raster')) == 'vtk':
        self.view_tool.set_engine(True, quiet=True)
