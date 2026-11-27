"""Compass: construction of the structure page (widgets, layout, signals; moved from workspace.py)."""

from PySide6.QtCore import QSize, Qt, QTimer
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QLabel,
    QWidget,
    QFrame,
    QButtonGroup,
    QScrollArea,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QPlainTextEdit,
    QTableWidget,
    QHeaderView,
    QTabBar,
    QTabWidget,
    QDoubleSpinBox,
    QLineEdit,
    QPushButton,
)

RAIL_WIDTH = 44  # px: 2026-11-17 — the column of the snapshot and the results at the right edge of the field
from azimuth.core import SYMBOLS, EXAMPLES
from modules.compass.view.viewer import MoleculeView
from azimuth.icons import icon, iconify
from modules.compass.chemistry.builder import (
    FRAGMENTS,
)
from modules.compass.panels.trajectory_drawer import TrajectoryDrawer

from azimuth.ui import label, button, card
from azimuth.i18n import tr
from modules.compass.panels.widgets import ElementTile, ExpandButton
from modules.compass.chemistry import library
from modules.compass.panels.layout_parts import ChoicePill, _MatchHeight, DeleteKey, side_slide_box


class StructurePage:
    """Mixin of CompassWorkspace: structure_page() builds the Compass page once."""

    def structure_page(self):
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(0, 0, 0, 0)
        frame, view_layout = card(tr('Структура молекулы'))
        view_layout.itemAt(0).widget().hide()
        view_layout.setContentsMargins(10, 10, 10, 10)
        view_layout.setSpacing(7)
        self.examples = QComboBox()
        self.examples.addItems(library.keys())  # the examples and the library
        self.examples.hide()
        self.structure_tabs = QTabWidget()
        self.structure_tabs.setObjectName('structureTabs')  # no tab bar — the pane keeps its top edge
        self.trajectory_button = iconify(
            button('', self.trajectory_tool.toggle_trajectory),
            'menu',
            tr('Результат расчёта: шаги оптимизации, частоты, орбитали, QTAIM'),
        )
        self.trajectory_button.setCheckable(True)
        # it stood above the tabs and made the row taller when it appeared; as tall as «Молекула |
        # Координаты» (follows their height, _MatchHeight), so the row keeps its height
        self.trajectory_button.setFixedSize(24, 24)
        self.trajectory_button.setIconSize(QSize(18, 18))
        # one row — the steps button, «Молекула | Координаты», a thin rule, the tabs of the documents.
        # The tab bar of structure_tabs is hidden; view_tabs shows its tabs (sync_view_tabs) in that row.
        self.structure_tabs.tabBar().hide()
        self.view_tabs = QTabBar()
        self.view_tabs.setObjectName('viewTabs')
        self.view_tabs.setDrawBase(False)
        self.view_tabs.setExpanding(False)
        self.view_tabs.currentChanged.connect(lambda i: self.structure_tabs.setCurrentIndex(i) if i >= 0 else None)
        self._match_height = _MatchHeight(self.view_tabs, self.trajectory_button)
        self.structure_tabs.currentChanged.connect(self._follow_structure_tab)
        self.document_row = self.build_view_row((self.trajectory_button, self.view_tabs))
        # the tabs on the very edge of the field — no spacing between the row and the field
        field = QVBoxLayout()
        field.setContentsMargins(0, 0, 0, 0)
        field.setSpacing(0)
        field.addWidget(self.document_row)
        field.addWidget(self.structure_tabs, 1)
        view_layout.addLayout(field, 1)
        self.browsing = False
        self.trajectory_initial = None
        self._own = None
        model = QWidget()
        model_layout = QVBoxLayout(model)
        model_layout.setContentsMargins(12, 12, 12, 12)
        controls = QHBoxLayout()
        self.build_mode = QComboBox(self)
        for title, mode in [
            (tr('Обзор / выделение'), 'view'),
            (tr('Добавить атом'), 'atom'),
            (tr('Добавить фрагмент'), 'fragment'),
            (tr('Переместить атом'), 'move'),
            (tr('Добавить молекулу'), 'molecule'),
        ]:
            self.build_mode.addItem(title, mode)
        self.molecule_choice = next(iter(EXAMPLES))
        self.build_mode.hide()
        # «Обзор / выделение» as a button of its own, the first of the modes — it was reached only by pressing the
        # pencil or the arrows again
        self.view_button = button('', self.choose_view_mode)
        self.view_button.setCheckable(True)
        self.view_button.setChecked(True)
        iconify(self.view_button, 'select',
                tr('Обзор / выделение · вращать модель, выделять атомы щелчком, рамкой — с Shift; структура не меняется'))
        controls.addWidget(self.view_button)
        self.edit_toggle = button(tr('Обзор'), self.toggle_edit_mode)
        self.edit_toggle.setCheckable(True)
        iconify(
            self.edit_toggle,
            'edit',
            tr('Изменение структуры · добавить атомы, фрагменты или выбрать молекулу'),
        )
        controls.addWidget(self.edit_toggle)
        self.move_button = button('', self.toggle_move_mode)
        self.move_button.setCheckable(True)
        iconify(
            self.move_button,
            'move',
            tr('Перемещение атомов · нажмите и перетаскивайте атом мышью'),
        )
        controls.addWidget(self.move_button)
        self.move_kind = QComboBox()
        for title, key in [
            (tr('Атом'), 'atom'),
            (tr('Фрагмент / угол'), 'fragment'),
            (tr('Молекула целиком'), 'molecule'),
            (tr('Выделенное'), 'selection'),
            (tr('Цепочка'), 'chain'),  # after the old ones, their numbers stay
            (tr('Вокруг связи'), 'twist'),
        ]:
            self.move_kind.addItem(title, key)
        self.move_kind.setToolTip(tr('Что перемещать мышью: атом, фрагмент вокруг опоры, молекулу целиком, цепочку или выделенное'))
        self.move_kind.currentIndexChanged.connect(self.change_move_target)
        self.element = QComboBox(self)
        self.element.addItems(list(SYMBOLS) + ['X'])  # and the dummy atom
        self.element.setCurrentText('C')
        self.element.hide()
        self.element_button = button('', self.toggle_periodic_table)
        self.element_button.setCheckable(True)
        iconify(self.element_button, 'element', tr('Атом · таблица Менделеева'))
        self.fragment_button = iconify(
            button('', lambda: self.model_menu_tool._popup(self.fragment_button, self.model_menu_tool.fragment_menu())),
            'fragment',
            tr('Фрагмент · выбрать группу для добавления'),
        )
        self.fragment_button.setCheckable(True)
        self.molecule_button = iconify(
            button('', lambda: self.model_menu_tool._popup(self.molecule_button, self.model_menu_tool.molecule_menu())),
            'molecule',
            tr('Молекула · выбрать и щёлкнуть в поле, чтобы добавить'),
        )
        self.molecule_button.setCheckable(True)
        self.hydrogens_button = iconify(
            button('', self.fill_hydrogens),
            'hydrogens',
            tr('Достроить водороды · у выделенных атомов, если они выбраны, иначе у всех'),
        )
        self.hydrogens_action = QAction(tr('Достроить водороды'), self)
        self.hydrogens_action.triggered.connect(self.fill_hydrogens)
        self.cleanup_button = iconify(
            button('', self.clean_geometry),
            'cleanup',
            tr('Выровнять геометрию · выделенного или всей молекулы'),  # short, it fits
        )
        self.cleanup_action = QAction(tr('Выровнять геометрию'), self)
        self.cleanup_action.triggered.connect(self.clean_geometry)
        # the universal force field — real energies (kcal/mol), uff.py
        self.uff_action = QAction(tr('Оптимизировать (UFF)'), self)
        self.uff_action.setToolTip(tr('Силовое поле UFF (Rappé и др., 1992; параметры RDKit): выделенные атомы или вся '
                                      'молекула; энергия и её слагаемые — в строке состояния'))
        self.uff_action.triggered.connect(self.optimize_uff)
        # flat (2D) structures of a file — three-dimensional by RDKit (embed3d.py)
        self.make_3d_action = QAction(tr('Сделать 3D (RDKit)…'), self)
        self.make_3d_action.setToolTip(tr('Объёмные координаты из RDKit (ETKDG + MMFF94): для выбранной молекулы '
                                          'проекта, в пакетном режиме — для плоских среди отмеченных'))
        self.make_3d_action.triggered.connect(lambda *_: self.opening_tool.make_3d())
        # tidy around every new atom or group right away (cleanup.tidy_new); remembered
        self.tidy_live_action = QAction(tr('Выравнивать при построении'), self)
        self.tidy_live_action.setCheckable(True)
        self.tidy_live_action.setToolTip(
            tr('Новый атом или группа сразу встают по VSEPR, цепочка вытягивается зигзагом; остальная молекула не двигается')
        )
        self.tidy_live_action.setChecked(str(self.preferences.value('tidy_live', 'true')).lower() in ('true', '1'))
        self.tidy_live_action.toggled.connect(lambda on: self.preferences.setValue('tidy_live', bool(on)))
        # «Выравнивать при построении» with UFF instead of the simple field
        self.tidy_uff_action = QAction(tr('Выравнивать по UFF'), self)
        self.tidy_uff_action.setCheckable(True)
        self.tidy_uff_action.setToolTip(tr('При построении новые атомы выравнивает силовое поле UFF, а не простое поле '
                                           'VSEPR (медленнее для больших молекул)'))
        self.tidy_uff_action.setChecked(str(self.preferences.value('tidy_uff', 'false')).lower() in ('true', '1'))
        self.tidy_uff_action.toggled.connect(lambda on: self.preferences.setValue('tidy_uff', bool(on)))
        # both switches as icon buttons in the structure tools, next to «Достроить водороды» and «Выровнять геометрию»
        self.tidy_live_button = iconify(
            button('', lambda: None),
            'tidy-live',
            tr('Выравнивать при построении · новый атом или группа сразу встают по VSEPR, цепочка — зигзагом'),
        )
        self.hydrogens_live_action = QAction(tr('Достраивать водороды при построении'), self)
        self.hydrogens_live_action.setCheckable(True)
        self.hydrogens_live_action.setToolTip(
            tr('Новый атом получает водороды по валентности; атом, к которому его ставят, отдаёт лишний водород')
        )
        self.hydrogens_live_action.setChecked(
            str(self.preferences.value('hydrogens_live', 'false')).lower() in ('true', '1')
        )
        self.hydrogens_live_action.toggled.connect(lambda on: self.preferences.setValue('hydrogens_live', bool(on)))
        self.hydrogens_live_button = iconify(
            button('', lambda: None),
            'hydrogens-auto',
            tr('Достраивать водороды при построении · по валентности атомов'),
        )
        for switch, action in (
            (self.tidy_live_button, self.tidy_live_action),
            (self.hydrogens_live_button, self.hydrogens_live_action),
        ):
            switch.setCheckable(True)
            switch.setChecked(action.isChecked())
            switch.toggled.connect(action.setChecked)
            action.toggled.connect(switch.setChecked)
        # the chosen fragment / molecule, next to its button; a click on it — their menu again, to choose another
        self.choice_label = ChoicePill(lambda: self.model_menu_tool._popup(
            self.choice_label, self.model_menu_tool.molecule_menu() if self.build_mode.currentData() == 'molecule'
            else self.model_menu_tool.fragment_menu()))
        self.choice_label.setToolTip(tr('Выбрать другой фрагмент или молекулу'))
        self.element_tile = ElementTile(self.toggle_periodic_table)
        self.element.currentTextChanged.connect(lambda *args: self.update_choice_label())
        self.move_kind_buttons = {}
        for key, name, title in [
            ('atom', 'move-atom', tr('Двигать атом')),
            ('fragment', 'move-fragment', tr('Двигать фрагмент · вокруг опорного атома')),
            ('twist', 'twist-plus', tr('Вращать вокруг связи · выделите два связанных атома и тяните атом одной из сторон')),
            ('molecule', 'move-molecule', tr('Двигать молекулу целиком · ту, к которой относится атом (в димере — одну)')),
            ('chain', 'move-chain', tr('Двигать цепочку · неразветвлённый участок до ближайших разветвлений и колец')),
            ('selection', 'move-selection', tr('Двигать выделенные атомы · Shift + протяжка — выделить рамкой')),
        ]:
            item = iconify(button('', lambda checked=False, k=key: self.choose_move_kind(k)), name, title)
            item.setCheckable(True)
            self.move_kind_buttons[key] = item
        self.fragment = QComboBox()
        self.fragment.addItems(FRAGMENTS)
        self.fragment_title = label(tr('Фрагмент'))
        self.fragment.setMinimumWidth(210)
        controls.setSpacing(6)
        controls.addSpacing(4)
        controls.addWidget(self.tool_rule())
        controls.addSpacing(4)  # modes | view tools
        model_layout.addLayout(controls)
        self.edit_tools = QWidget()
        edit_row = QHBoxLayout(self.edit_tools)
        edit_row.setContentsMargins(0, 0, 0, 0)
        self.add_atom_button = iconify(
            button('', self.add_atom), 'atom', tr('Добавить атом · выбрать элемент в таблице Менделеева')
        )
        self.add_fragment_button = iconify(
            button('', lambda: self.select_mode(2)), 'fragment', tr('Добавить фрагмент · выбрать шаблон молекулы')
        )
        edit_row.setSpacing(6)
        for item in (self.add_atom_button, self.add_fragment_button):
            item.setCheckable(True)
            item.hide()
        for item in (self.fragment_title, self.fragment, self.move_kind):
            edit_row.addWidget(item)
            item.hide()
        # the choice stands next to its button: atom [C], fragment [—OH], molecule [вода]
        for item in (
            self.element_button,
            self.element_tile,
            self.fragment_button,
            self.choice_label,
            self.molecule_button,
        ):
            edit_row.addWidget(item)
        self.edit_rule = self.tool_rule()
        edit_row.addSpacing(4)
        edit_row.addWidget(self.edit_rule)
        edit_row.addSpacing(4)  # adding | tidying
        for item in (
            self.hydrogens_button,
            self.hydrogens_live_button,
            self.cleanup_button,
            self.tidy_live_button,
            *self.move_kind_buttons.values(),
        ):
            edit_row.addWidget(item)
        self.edit_row = edit_row
        edit_row.addStretch()
        model_layout.addWidget(self.edit_tools)
        edits = QHBoxLayout()
        self.bond_order = QComboBox()
        self.bond_order.addItems(['1', '2', '3'])
        self.bond_order.setMinimumWidth(66)
        self.bond_order_title = label(tr('Порядок связи'))
        edit_row.addWidget(self.bond_order_title)
        edit_row.addWidget(self.bond_order)
        self.bond_length = QDoubleSpinBox()
        self.bond_length.setRange(0, 5)
        self.bond_length.setDecimals(2)
        self.bond_length.setSingleStep(0.05)
        self.bond_length.setSpecialValueText(tr('Авто'))
        self.bond_length.hide()
        self.bond_button = button(tr('Связать'), self.apply_bond)
        self.bond_button.hide()
        self.unbond_button = button(tr('Разорвать'), lambda: self.apply_bond(remove=True))
        self.unbond_button.hide()
        self.delete_button = button(tr('Удалить'), self.remove_atom)
        self.delete_button.hide()
        edits.addStretch()
        self.undo_button = button(tr('↶ Отмена'), self.undo_geometry)
        self.redo_button = button(tr('↷ Повтор'), self.redo_geometry)
        self.undo_button.hide()
        self.redo_button.hide()
        self.viewer = MoleculeView()
        self.viewer.isotope_source = lambda: getattr(self, '_isotopes', '')  # D, ¹³C … on the model
        self.center_button = button(tr('Центровать'), self.viewer.center_view)
        iconify(
            self.center_button, 'center', tr('Центровать · Пробел на модели; сохранить ориентацию и подобрать масштаб')
        )
        self.projection = QComboBox()
        self.projection.addItems(['Isometry', 'Perspective'])
        self.projection.setItemIcon(0, icon('isometry'))
        self.projection.setItemIcon(1, icon('perspective'))
        self.projection.hide()
        self.projection_buttons = []
        # one of the two always on — a second press on the one that is on leaves it on
        self.projection_group = QButtonGroup(self)
        self.projection_group.setExclusive(True)
        for i, name in enumerate(('isometry', 'perspective')):
            b = iconify(
                button('', lambda checked=False, n=i: self.projection.setCurrentIndex(n)),
                name,
                tr('Изометрия') if i == 0 else tr('Перспектива'),
            )
            b.setCheckable(True)
            b.setChecked(i == 0)
            self.projection_group.addButton(b)
            self.projection_buttons.append(b)
        self.projection.currentIndexChanged.connect(self.change_projection)
        # named as in «Вид»
        self.best_button = iconify(button('', self.viewer.best_view), 'best',
                                   tr('Лучший ракурс · повернуть молекулу длинной стороной поперёк и плоскостью к вам, '
                                      'затем центровать'))
        self.axes_button = button(tr('Оси'), self.toggle_axes)
        self.axes_button.setCheckable(True)
        iconify(self.axes_button, 'axes', tr('Показать оси · направления X, Y, Z'))
        # — in the menu of the button of the panel (custom_bar.button_menu), above its own items
        self.axes_button.own_menu = self.fill_axes_menu
        self.restore_axes_place()
        # the unit cell switch of «Компас · Кристалл» stands next to the axes (hidden in the molecule
        # mode without keeping its place — the empty gap next to the axes is gone)
        self.cell_button = iconify(button('', lambda: self.crystal_tool.toggle_cell_button()), 'cell', tr('Показывать ячейку кристалла'))
        self.cell_button.setCheckable(True)
        self.cell_button.setChecked(True)
        self.cell_button.hide()  # no empty place for it in «Компас · Молекула»
        # the tools of a crystal next to the cell switch; shown in «Компас · Кристалл» only (crystal_tool.update_panel)
        def side(kind, opener):  # a button of a panel beside the model opens it and folds it again
            return lambda *_: self.crystal_tool.toggle_side(kind, opener)

        self.crystal_info_button = iconify(button('', side('crystal', lambda: self.crystal_tool.reopen_crystal())), 'crystal',
                                           tr('Кристалл · сведения, ячейки, поверхность (hkl), операции симметрии'))
        self.crystal_view_button = iconify(
            button('', lambda: self.model_menu_tool._popup(self.crystal_view_button, self.crystal_tool.view_menu())),
            'surface-slab', tr('Вид кристалла · вдоль a, b, c; элементы симметрии, эллипсоиды, полиэдры'))
        self.contacts_button = iconify(button('', side('contacts', lambda: self.crystal_tool.show_contacts())), 'ruler',
                                       tr('Контакты и водородные связи между молекулами кристалла'))
        self.powder_button = iconify(button('', lambda: self.crystal_tool.show_powder()), 'spectrum',
                                     tr('Порошковая дифрактограмма кристалла'))
        # no button of Quantum ESPRESSO — the calculation of a crystal is set in Sextant
        def hirshfeld():
            from modules.compass.actions import hirshfeld_window

            return hirshfeld_window.show(self)

        # the Hirshfeld surface on the panel of a crystal too (it was in «Кристалл» of the menu only)
        self.hirshfeld_button = iconify(button('', side('hirshfeld', hirshfeld)), 'hirshfeld',
                                        tr('Поверхность Хиршфельда молекулы кристалла · dnorm, отпечатки контактов'))
        def results():
            from modules.compass.actions import crystal_results_panel

            return crystal_results_panel.show(self)

        # the runs of the crystal and what they gave — a panel beside the model (crystal_results_panel)
        self.crystal_results_button = iconify(button('', side('results', results)), 'output',
                                              tr('Результаты расчётов кристалла · энергии, давление, зона, шаги, папки'))
        self.crystal_buttons = (self.crystal_info_button, self.crystal_view_button, self.contacts_button, self.powder_button,
                                self.hirshfeld_button, self.crystal_results_button)
        for item in self.crystal_buttons:
            item.hide()
        for item in (self.crystal_info_button, self.contacts_button, self.hirshfeld_button, self.crystal_results_button):
            item.setCheckable(True)  # lit while its panel is shown (crystal_tool.sync_side_buttons)
        self.lengths_button = QPushButton()
        self.lengths_button.setCheckable(True)
        self.lengths_button.hide()  # bond lengths: «Вид»
        self.symmetry_button = iconify(
            button('', self.symmetry_tool.determine_symmetry),  # find the group on demand, then symmetrise
            'symmetry',
            tr('Определить точечную группу · повторное нажатие — симметризовать'),
        )
        self.lock_button = iconify(
            button('', lambda: self.model_menu_tool._popup(self.lock_button, self.constraint_tool.menu())),
            'lock',
            tr('Ограничения оптимизации · закрепить атом, длину, угол или двугранный угол (1–4 выделенных атома)'),
        )
        self.constraints = []
        self.lock_action = QAction(tr('Закрепить выделенное для оптимизации'), self)
        self.lock_action.triggered.connect(lambda: self.constraint_tool.toggle())
        self.symmetry_tol = self.preferences.value('symmetry_tol', 0.1)
        try:
            self.symmetry_tol = float(self.symmetry_tol)
        except (TypeError, ValueError):
            self.symmetry_tol = 0.1
        if self.symmetry_tol not in (0.05, 0.1, 0.2, 0.3, 0.5):
            self.symmetry_tol = 0.1
        self.symmetry_result = None
        self._symmetry_key = None
        self.symmetrize_action = QAction(tr('Симметризовать'), self)
        self.symmetrize_action.triggered.connect(lambda: self.symmetry_tool.apply_symmetry(False))
        self.standard_action = QAction(tr('Симметризовать и повернуть в стандартную ориентацию'), self)
        self.standard_action.triggered.connect(lambda: self.symmetry_tool.apply_symmetry(True))
        self.symmetry_timer = QTimer(self)
        self.symmetry_timer.setSingleShot(True)
        self.symmetry_timer.setInterval(180)
        self.symmetry_timer.timeout.connect(self.symmetry_tool.update_symmetry)
        self.display_mode = QComboBox()
        for title, key in [
            (tr('Шары и стержни'), 'ball-stick'),
            (tr('Стержни'), 'sticks'),
            (tr('Пространственная модель'), 'spacefill'),
        ]:
            self.display_mode.addItem(title, key)
        self.display_mode.setMaximumWidth(200)
        self.display_mode.setToolTip(
            tr(
                'Вид молекулы. Пространственная модель: радиусы H/C/N/O по Бонди; для остальных элементов условный радиус 1.8 Å.'
            )
        )
        self.display_mode.setCurrentIndex(
            max(0, self.display_mode.findData(self.preferences.value('display_mode', 'ball-stick')))
        )
        self.display_mode.currentIndexChanged.connect(self.change_display_mode)
        self.display_mode.hide()
        self.change_display_mode()
        canvas = QHBoxLayout()
        # the spacing of the row taken into
        # the panel and the box of its line — with the panel folded they are nothing, and the field comes up to the
        # line itself before it goes (the spacing round a panel of width 0 kept the field away from it)
        gap = canvas.spacing()
        if gap < 0:
            from PySide6.QtWidgets import QStyle

            gap = self.style().pixelMetric(QStyle.PixelMetric.PM_LayoutHorizontalSpacing)
        self.view_panel_gap = max(0, gap) if gap >= 0 else 6
        canvas.setSpacing(0)
        canvas.addWidget(self.viewer, 1)
        # a side panel between the field and the view panel — they open in it, the model
        # stays in sight and follows them (crystal_actions.CrystalTool.dock)
        self.crystal_side = QFrame()
        self.crystal_side.setObjectName('crystalSide')
        side_layout = QVBoxLayout(self.crystal_side)
        side_layout.setContentsMargins(8, 0, 4, 0)
        side_layout.setSpacing(0)
        self.crystal_side.setMinimumWidth(500)
        self.crystal_side.setMaximumWidth(620)
        self.crystal_side.hide()
        # the panel in a box whose width slides (crystal_actions.CrystalTool.slide_side); the panel keeps its width at
        # the left edge of the box, so it comes out from under the view panel as the drawer of the molecules does
        canvas.addWidget(side_slide_box(self.crystal_side))
        self.view_panel = QScrollArea()
        self.view_panel.setWidgetResizable(True)
        from modules.compass.actions.view_actions import VIEW_PANEL_WIDTH

        self.view_panel.setFixedWidth(VIEW_PANEL_WIDTH + self.view_panel_gap)  # the two columns closer
        self.view_panel.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.view_panel.setFrameShape(QFrame.Shape.NoFrame)
        panel_content = QWidget()
        # clipped while the panel folds, not laid out again at every step
        panel_content.setMinimumWidth(VIEW_PANEL_WIDTH + self.view_panel_gap)
        self.view_panel.setWidget(panel_content)
        rotation = QVBoxLayout(panel_content)
        rotation.setContentsMargins(self.view_panel_gap, 0, 0, 0)  # the spacing from the field, inside
        rotation.setSpacing(6)
        self.rotation_title = label(tr('Вращение вида'), 'subtitle')
        self.rotation_title.hide()  # the tooltips say what turns (the view, or the fragment while editing)
        self.rotation_buttons = []

        def button_pair():
            pair = QHBoxLayout()
            pair.setContentsMargins(0, 0, 0, 0)
            pair.setSpacing(4)
            pair.addStretch(1)
            return pair

        for axis in 'xyz':
            pair = button_pair()
            for direction in [-1, 1]:
                b = self.hold_button(
                    'rotate-' + axis + ('-minus' if direction < 0 else '-plus'),
                    tr('Вращение ') + axis.upper() + tr(' · щелчок 15°, удержание — плавно'),
                    lambda a=axis, d=direction: self.rotate_control(a, d),
                    lambda a=axis, d=direction: self.rotate_control(a, d, 4.5),
                )
                pair.addWidget(b)
                self.rotation_buttons.append(b)
            pair.addStretch(1)
            rotation.addLayout(pair)
        self.fragment_controls = QWidget()
        fc = QVBoxLayout(self.fragment_controls)
        fc.setContentsMargins(0, 10, 0, 4)
        fc.setSpacing(6)
        fc.addWidget(self.panel_rule())
        for title, callback in [
            (tr('Крутить −'), lambda: self.twist_fragment(-1)),
            (tr('Крутить +'), lambda: self.twist_fragment(1)),
            (tr('Длина −'), lambda: self.stretch_selected(-0.05)),
            (tr('Длина +'), lambda: self.stretch_selected(0.05)),
        ]:
            if title in (tr('Крутить −'), tr('Длина −')):
                fc_pair = button_pair()
                fc.addLayout(fc_pair)
            name = {
                tr('Крутить −'): 'twist-minus',
                tr('Крутить +'): 'twist-plus',
                tr('Длина −'): 'length-minus',
                tr('Длина +'): 'length-plus',
            }[title]
            direction = -1 if title.endswith('−') else 1
            tick = (
                (lambda d=direction: self.twist_fragment(d, 4.5))
                if title.startswith(tr('Крутить'))
                else (lambda d=direction: self.stretch_selected(d * 0.01))
            )
            b = self.hold_button(
                name, title + tr(' · два связанных атома; щелчок — шаг, удержание — плавно'), callback, tick
            )
            fc_pair.addWidget(b)
            if direction > 0:
                fc_pair.addStretch(1)
        rotation.addWidget(self.fragment_controls)
        rotation.addSpacing(4)
        rotation.addWidget(self.panel_rule())
        rotation.addSpacing(4)
        self.view_buttons = []
        for row in [
            [
                ('zoom-in', tr('Приблизить'), lambda: self.viewer.zoom_view(1.15), lambda: self.viewer.zoom_view(1.03)),
                (
                    'zoom-out',
                    tr('Отдалить'),
                    lambda: self.viewer.zoom_view(1 / 1.15),
                    lambda: self.viewer.zoom_view(1 / 1.03),
                ),
            ],
            [
                (
                    'pan-left',
                    tr('Сместить вид влево'),
                    lambda: self.viewer.pan_view(-20, 0),
                    lambda: self.viewer.pan_view(-8, 0),
                ),
                (
                    'pan-right',
                    tr('Сместить вид вправо'),
                    lambda: self.viewer.pan_view(20, 0),
                    lambda: self.viewer.pan_view(8, 0),
                ),
            ],
            [
                (
                    'pan-up',
                    tr('Сместить вид вверх'),
                    lambda: self.viewer.pan_view(0, -20),
                    lambda: self.viewer.pan_view(0, -8),
                ),
                (
                    'pan-down',
                    tr('Сместить вид вниз'),
                    lambda: self.viewer.pan_view(0, 20),
                    lambda: self.viewer.pan_view(0, 8),
                ),
            ],
        ]:
            pair = button_pair()
            for name, title, step, tick in row:
                b = self.hold_button(name, title + tr(' · можно удерживать'), step, tick)
                pair.addWidget(b)
                self.view_buttons.append(b)
            pair.addStretch(1)
            rotation.addLayout(pair)
        rotation.addStretch()
        # a slim column with a chevron between the field and the panel; the panel folds to nothing
        # and opens again smoothly (view_actions.set_view_panel_open), the choice remembered
        self.view_panel_toggle = iconify(button('', lambda: self.view_tool.set_view_panel_open(not self.view_tool.view_panel_open())),
                                         'panel-toggle', tr('Свернуть панель вида'))
        self.view_panel_toggle.setFixedSize(RAIL_WIDTH, 30)
        self.view_panel_toggle.setIconSize(QSize(16, 16))
        canvas.addWidget(self.view_panel)
        # the chevron of the view panel ends the row of tools (above the rail); the rail stands at the
        # very edge, and the panel comes out between the field and it — the rail never moves
        self.view_panel_motion = None
        if str(self.preferences.value('view_panel_open', 'true')).lower() in ('false', '0'):
            self.view_tool.set_view_panel_open(False, animate=False)
        model_layout.addLayout(canvas, 1)
        self.drawer = TrajectoryDrawer(model)
        self.drawer.stepChanged.connect(self.trajectory_tool.show_trajectory_step)
        self.drawer.adoptRequested.connect(self.trajectory_tool.adopt_trajectory_step)
        self.drawer.mapRequested.connect(self.trajectory_tool.open_scan_map)
        self.drawer.openRequested.connect(self.trajectory_tool.open_calculation_folder)  # was open_trajectory
        self.drawer.closeRequested.connect(lambda: self.trajectory_tool.set_trajectory_open(False, keep=True))
        self.drawer.spectrumRequested.connect(lambda page: self.open_spectrum_for(page))
        self.drawer.initialToggled.connect(lambda *args: self.trajectory_tool.show_trajectory_step(self.drawer.current))
        # the pages of the drawer — the vibrations move on the model; the orbitals and QTAIM are pages too
        self.drawer.pageChanged.connect(self.trajectory_tool.apply_drawer_page)
        self.drawer.conformerChanged.connect(self.trajectory_tool.show_conformer)
        self.drawer.conformerAdoptRequested.connect(self.trajectory_tool.adopt_conformer)
        self.drawer.modeFrame.connect(self.trajectory_tool.show_mode_frame)
        self.density_tool.build_density_drawer(self.drawer)
        # 0.247.0: no Quill with her bubble in the empty field (the owner: «убрать совсем») — the field itself says how
        # to begin, in a molecule and in a crystal (Workspace.update_side_quill, viewer.empty_parts)
        self.quill_hint = self.crystal_hint = None
        for watched in (self.viewer, self.drawer, self.drawer.table, self.drawer.modes_table):
            watched.installEventFilter(self)
        self.label_mode = QComboBox()
        for title, key in [
            (tr('Элемент · C'), 'element'),
            (tr('Номер · 1'), 'number'),
            (tr('Элемент и номер · C1'), 'both'),
            (tr('Номер в элементе · C1, H1'), 'group'),  # C1, C2… H1, H2… (as Chemcraft)
        ]:
            self.label_mode.addItem(title, key)
        self.label_mode.setCurrentIndex(
            max(0, self.label_mode.findData(self.preferences.value('atom_labels', 'element')))
        )
        self.label_mode.currentIndexChanged.connect(self.change_labels)
        self.label_buttons = {}
        # small groups — modes | centre, best view | projection | axes | labels | constraints … snapshot
        # the label buttons stand with the other view tools, between rules
        for caption, key in [('1', 'number'), ('H', 'element'), ('H1', 'both')]:
            item = button(caption, lambda checked=False, k=key: self.toggle_label(k))
            item.setCheckable(True)
            item.setFixedSize(36, 36)
            # one text with {} — a text
            # glued of three translated pieces was not known to the change of the language
            iconify(item, 'label-' + key, tr('Подпись {}').format(caption))  # no «a second click turns it off» in the
            # tip
            self.label_buttons[key] = item
        # own labels of atoms — select atoms, press it and write the label; without a selection it shows or
        # hides the own labels
        self.custom_label_button = iconify(
            button('', self.edit_custom_labels), 'label-custom',
            tr('Своя подпись выделенных атомов · без выделения — показать или скрыть свои подписи'),
        )
        self.custom_label_button.setCheckable(True)
        self.custom_label_button.setChecked(True)
        # the row is groups of buttons parted by lines — laid by modules/compass/actions/custom_bar.py, where
        # the user moves, adds and takes away buttons (the groups from the start below, DEFAULT_GROUPS)
        from modules.compass.actions import custom_bar

        top_area = QHBoxLayout()
        top_area.setContentsMargins(0, 0, 0, 0)
        top_area.setSpacing(6)
        controls.addLayout(top_area)
        controls.addStretch()
        # the snapshot and the results laid over the model stand in a column at the right edge of the field (rail,
        # below); the row keeps the tools up to the lock — the place of the user's own buttons later
        rail = QWidget()
        rail.setObjectName('toolRail')
        rail.setFixedWidth(RAIL_WIDTH)
        rail_column = QVBoxLayout(rail)
        rail_column.setContentsMargins(0, 0, 0, 0)
        rail_column.setSpacing(4)
        self.tool_rail = rail
        # «±» split into three — the values at the atoms, the bond orders, the arrows
        self.property_buttons = {}
        for part, name, tip in (
            ('atoms', 'charges', tr('Атомы из расчёта · заряды (Малликен, Лёвдин, Хиршфельд, ADCH, CM5, RESP, AIM), '
                                    'спиновые заселённости, валентности, функции Фукуи')),
            ('bonds', 'bond-orders', tr('Связи из расчёта · порядки связей Майера, Виберга, FBO, LBO на модели; '
                                        'связи структуры по порядкам')),
            ('vectors', 'dipole', tr('Диполь и силы · дипольный момент и силы на атомах стрелками')),
        ):
            item = iconify(button('', lambda checked=False, p=part: self.property_tool.show_property_menu(p)), name, tip)
            self.property_buttons[part] = item
        self.properties_button = self.property_buttons['atoms']
        # one press takes everything laid over the structure away — properties, surfaces, critical points
        self.clear_overlays_button = iconify(button('', lambda: self.property_tool.clear_model_overlays()), 'clear-model',
                                             tr('Убрать с модели всё наложенное · заряды, порядки связей, диполь, '
                                                'поверхности, критические точки'))
        # the button is kept, hidden — «Инструменты → Сравнение структур» opens the same menu (in the menus of the hub)
        self.compare_button = iconify(
            button('', lambda: self.model_menu_tool._popup(self.compare_button, self.compare_menu)),
            'overlay',
            tr('Сравнить с другой структурой · наложение, RMSD, атомы в любом порядке'),
        )
        self.compare_button.hide()
        self.compare_button.setProperty('azimuthAway', True)  # crystal_actions.update_panel leaves it hidden
        self.screenshot_button = iconify(
            button('', lambda: self.model_menu_tool._popup(self.screenshot_button, self.picture_tool.snapshot_menu())),
            'camera',
            tr('Снимок · PNG, высокое разрешение, прозрачный фон, GIF вращения или шагов оптимизации'),
        )
        under = QFrame()
        # a thin rule under the <> button, as under the camera
        under.setObjectName('toolRule')
        under.setFixedSize(22, 1)
        rail_column.addWidget(under, 0, Qt.AlignmentFlag.AlignHCenter)
        rail_area = QVBoxLayout()
        rail_area.setContentsMargins(0, 2, 0, 0)
        rail_area.setSpacing(4)
        rail_column.addLayout(rail_area)
        rail_column.addStretch(1)
        widgets = {'center': self.center_button, 'best': self.best_button, 'axes': self.axes_button,
                   'cell': self.cell_button, 'label-number': self.label_buttons['number'],
                   'label-element': self.label_buttons['element'], 'label-both': self.label_buttons['both'],
                   'label-custom': self.custom_label_button, 'lock': self.lock_button,
                   'snapshot': self.screenshot_button, 'atoms': self.property_buttons['atoms'],
                   'bonds': self.property_buttons['bonds'], 'vectors': self.property_buttons['vectors'],
                   'clear': self.clear_overlays_button}
        widgets.update({f'projection-{k}': item for k, item in enumerate(self.projection_buttons)})
        # the names kept by the panels of the users — crystal-4 was «Quantum ESPRESSO» (gone), the others stay
        widgets.update({f'crystal-{k}': item for k, item in zip((0, 1, 2, 3, 5, 6), self.crystal_buttons)})
        d = lambda *names: ['default:' + n for n in names]  # noqa: E731
        projections = d(*(f'projection-{k}' for k in range(len(self.projection_buttons))))
        labels = d('label-number', 'label-element', 'label-both', 'label-custom')
        defaults = {
            custom_bar.TOP: [d('center', 'best'), projections, d('axes'), labels, d('lock')],
            custom_bar.RAIL: [d('snapshot'), d('atoms', 'bonds', 'vectors', 'clear')],
        }
        # a panel of its own — the cell and the view of the crystal, its analyses, its
        # calculation; no constraints of an optimisation, no dipole; changed by the user apart from the molecule one
        crystal = {
            custom_bar.TOP: [d('center', 'best'), projections, d('axes', 'cell'), d('crystal-0', 'crystal-1'),
                             d('crystal-2', 'crystal-5', 'crystal-3'), d('crystal-6'), labels],
            custom_bar.RAIL: [d('snapshot'), d('atoms', 'bonds', 'clear')],
        }
        self.custom_bar = custom_bar.CustomBar(self, top_area, rail_area, defaults, {'crystal': crystal})
        self.custom_bar.enable(model, rail, controls)  # buttons dragged between the two
        for name, item in widgets.items():
            self.custom_bar.register(name, item)
        self.custom_bar.rebuild(panel=False)  # the buttons from the start laid now; the user's after the menus (start)
        # a thin upright line between the view panel and the column
        line = QFrame()
        line.setObjectName('toolRule')
        line.setFixedWidth(1)
        line.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)
        # the gap and the line in a box of their own at the right of the panel;
        # the folding takes the panel and then the box (view_actions.EDGE_GAP), so the field comes up to the line and
        # covers it
        from modules.compass.actions.view_actions import EDGE_GAP

        edge = QWidget()
        edge_row = QHBoxLayout(edge)
        edge_row.setContentsMargins(0, 0, 0, 0)
        edge_row.setSpacing(0)
        edge_row.addStretch(1)
        edge_row.addWidget(line)
        edge.setFixedWidth(self.view_panel_gap + EDGE_GAP)
        canvas.addWidget(edge)
        canvas.addSpacing(self.view_panel_gap)  # the spacing before the column, as before
        # the line stands with the open view panel (view_actions.set_view_panel_open), not by the field alone
        self.view_panel_edge = edge
        edge.setVisible(self.view_tool.view_panel_open())
        canvas.addWidget(rail)
        controls.addWidget(self.view_panel_toggle)
        self.label_mode.addItem(tr('Нет'), 'none')
        self.label_mode.hide()
        self.label_mode.setCurrentIndex(
            max(0, self.label_mode.findData(self.preferences.value('atom_labels', 'element')))
        )
        self.change_labels()
        self.measure_bar = QWidget()
        values = QHBoxLayout(self.measure_bar)
        values.setContentsMargins(0, 0, 0, 0)
        values.setSpacing(5)
        self.measure_fields = []
        for i, title in enumerate(['X', 'Y', 'Z', 'r / ∠']):
            if i:
                values.addSpacing(3)
            caption = label(title + ':', 'subtitle')
            # the captions keep their width, the row does not squeeze them
            caption.setWordWrap(False)
            caption.setMinimumWidth(caption.sizeHint().width())
            values.addWidget(caption)
            field = QLineEdit()
            field.setReadOnly(True)
            field.setFixedSize(80 if i == 3 else 60, 22)
            field.setObjectName('measure')
            values.addWidget(field)
            self.measure_fields.append(field)
        self.pin_button = iconify(
            button('', self.toggle_pin),
            'ruler',
            tr('Показать на модели: расстояние (2 атома), угол (3) или двугранный угол (4)'),
        )
        self.pin_button.setCheckable(True)
        self.pin_button.setFixedSize(28, 28)
        self.pin_button.setIconSize(QSize(18, 18))
        self.pin_button.setEnabled(False)
        values.addWidget(self.pin_button)
        values.addSpacing(6)
        self.measure_fields[3].returnPressed.connect(self.apply_measurement)
        from PySide6.QtWidgets import QSizePolicy

        self.measure_bar.setSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Fixed)  # not narrower than it needs
        self.geometry_modes = QButtonGroup(self)
        self.geometry_modes.setExclusive(True)
        self.geometry_fragment = iconify(
            button('', lambda: None),
            'geometry-fragment',
            tr(
                'Двигать фрагмент · при вводе длины/угла перемещается связанная часть; угол меняют обе стороны поровну'
            ),
        )
        self.geometry_atom = iconify(
            button('', lambda: None),
            'geometry-atom',
            tr(
                'Двигать последний атом · при вводе длины/угла остальные атомы неподвижны; соседние связи могут деформироваться'
            ),
        )
        for item in (self.geometry_fragment, self.geometry_atom):
            item.setCheckable(True)
            item.setFixedSize(28, 28)
            item.setIconSize(QSize(18, 18))
            self.geometry_modes.addButton(item)
            values.addWidget(item)
        self.geometry_fragment.setChecked(True)
        # one line that ends in «…» (the whole in the tooltip) — its width no longer follows the text: a long
        # «Выбраны: …» widened the row, the page reflowed and the fields of the values jumped
        from azimuth.ui import ElideLabel

        self.selection_info = ElideLabel('', 'subtitle')
        values.addSpacing(10)
        values.addWidget(self.selection_info, 1)
        self.viewer.update_help()
        self.structure_tabs.addTab(model, tr('Молекула'))
        coordinates = QWidget()
        editor_layout = QVBoxLayout(coordinates)
        editor_layout.setContentsMargins(12, 12, 12, 12)
        options = QHBoxLayout()
        self.coord_format = QComboBox()
        self.coord_format.addItems(
            [tr('Таблица'), 'XYZ', 'ORCA', 'Gaussian', 'NWChem', 'Z-matrix', 'MOL', 'SDF', 'MOL2', 'PDB', 'SMILES', 'InChI']
        )
        self.coord_format.addItem(tr('Дробные (CIF)'), 'fractional')  # «Компас · Кристалл» only
        self.coord_format.view().setRowHidden(self.coord_format.count() - 1, True)
        # the formats of a crystal, its only
        for text, data in ((tr('Независимые атомы (доли)'), 'sites'), (tr('CIF кристалла'), 'cif'),
                           ('POSCAR (VASP)', 'poscar'), (tr('Расширенный XYZ'), 'extxyz')):
            self.coord_format.addItem(text, data)
            self.coord_format.view().setRowHidden(self.coord_format.count() - 1, True)
        self.coord_units = QComboBox()
        self.coord_units.addItems([tr('Ангстремы (Å)'), tr('Боры (a₀)')])
        from azimuth import defaults

        self._coordinate_bohr = defaults.get('coordinate_unit') == 'bohr'  # «Настройки → Единицы»
        self.coord_units.setCurrentIndex(int(self._coordinate_bohr))
        options.addWidget(label(tr('Формат') + ':'))
        options.addWidget(self.coord_format)
        options.addWidget(label(tr('Единицы') + ':'))
        options.addWidget(self.coord_units)
        options.addStretch()
        options.addWidget(iconify(button('', self.coordinate_tool.copy_coordinates), 'copy', tr('Копировать координаты')))
        editor_layout.addLayout(options)
        self.coord_note = label('', 'subtitle')
        editor_layout.addWidget(self.coord_note)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr('Атом'), 'X', 'Y', 'Z'])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.table.itemChanged.connect(self.coordinate_tool.table_changed)
        self.table.itemSelectionChanged.connect(self.coordinate_tool.table_selection_changed)
        self._delete_key = DeleteKey(self.table, self.remove_atom)
        editor_layout.addWidget(self.table, 1)
        # the independent atoms of the crystal of the file (its sites) in fractions of the cell — «Компас ·
        # Кристалл», the format «Независимые атомы (доли)»; read-only, a row chosen selects its copies on the model
        self.site_table = QTableWidget(0, 7)
        self.site_table.setObjectName('siteTable')
        self.site_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.site_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.site_table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        self.site_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.site_table.itemSelectionChanged.connect(self.coordinate_tool.site_selection_changed)
        self.site_table.hide()
        editor_layout.addWidget(self.site_table, 1)
        self.coord_text = QPlainTextEdit()
        self.coord_text.setReadOnly(True)
        self.coord_text.hide()
        editor_layout.addWidget(self.coord_text, 1)
        self.coord_format.currentIndexChanged.connect(self.coordinate_tool.coordinate_format_changed)
        self.coord_units.currentIndexChanged.connect(self.coordinate_tool.coordinate_units_changed)
        tools = QHBoxLayout()
        tools.addWidget(iconify(button('', self.add_atom), 'atom', tr('Добавить атом на модели')))
        tools.addWidget(iconify(button('', self.remove_atom), 'delete', tr('Удалить выбранные атомы')))
        tools.addStretch()
        editor_layout.addLayout(tools)
        self.structure_tabs.addTab(coordinates, tr('Координаты'))
        self.sync_view_tabs()
        self.geometry_error = label('', 'error')
        self.geometry_error.hide()
        view_layout.addWidget(self.geometry_error)
        bottom = QHBoxLayout()
        bottom.setSpacing(10)
        bottom.addWidget(self.measure_bar, 3)  # room for the elided selection line
        # no status line under the field (the messages did not fit in it): a short message is a rounded
        # pill over the bottom of the model, wrapped when long, gone after its time
        self.notice = QLabel(self.viewer.parentWidget())
        self.notice.setObjectName('toast')
        self.notice.setWordWrap(True)
        self.notice.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.notice.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.notice.hide()
        self.notice_timer = QTimer(self)
        self.notice_timer.setSingleShot(True)
        self.notice_timer.timeout.connect(self.hide_notice)
        bottom.addStretch(1)
        self.molecule_info = label('', 'subtitle')
        self.molecule_info.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        self.molecule_info.setWordWrap(False)
        self.iupac_button = iconify(
            button('', self.naming_tool.show_iupac_name),
            'iupac',
            tr('Назвать молекулу по IUPAC · на языке программы; что не описано правилами — из PubChem'),
        )
        bottom.addWidget(self.iupac_button)
        bottom.addWidget(self.molecule_info)
        bottom.addWidget(self.symmetry_button)
        # in «Компас · Кристалл» the arrow takes the selected molecules to «Компас · Молекула» (the way to a
        # calculation); with nothing selected — to the calculation of the crystal in Sextant (Quantum ESPRESSO)
        self.next_button = ExpandButton(tr('К параметрам расчёта'), lambda: self.crystal_tool.to_calculation()
                                        if getattr(self, 'compass_mode', 'molecule') == 'crystal' else self.navigate(1))
        bottom.addWidget(self.next_button)
        view_layout.addLayout(bottom)
        self.structure_tabs.currentChanged.connect(lambda i: self.measure_bar.setVisible(i == 0))
        layout.addWidget(frame)
        self.stack.addWidget(page)
        self.viewer.placementRequested.connect(self.place_on_model)
        # an atom or a fragment aimed by a drag from an atom — shown while the mouse moves, put on release
        self.viewer.placement_aim = self.placement_preview
        self.viewer.placementAimed.connect(lambda anchor, direction: self.place_on_model(None, anchor, direction))
        # … and ended on another atom — that atom becomes the one dragged, bonded (snap_preview, snap_on_model)
        self.viewer.placement_snap = self.snap_preview
        self.viewer.placementSnapped.connect(self.snap_on_model)
        self.viewer.atomMoved.connect(self.move_on_model)
        self.viewer.moleculeMoved.connect(lambda m: self.commit_fragment_edit(m, self.viewer.selected.copy()))
        self.viewer.editError.connect(self.error)
        # a click on the empty field folds the drawer of the result (as ☰ does: the chosen step stays)
        self.viewer.emptyClicked.connect(
            lambda: self.trajectory_tool.set_trajectory_open(False, keep=True) if self.trajectory_button.isChecked() else None)
        self.viewer.emptyClicked.connect(lambda: self.surface_tool.unmark_aim())  # the ring of a point goes
        self.viewer.contactClicked.connect(lambda h, a: self.crystal_tool.contact_clicked(h, a))
        # a click on the field past the atoms folds the panel beside the model of a crystal
        self.viewer.emptyClicked.connect(lambda: self.crystal_tool.empty_field_clicked())
        self.viewer.selectionChanged.connect(self.model_selection_changed)
        self.viewer.deleteRequested.connect(self.remove_atom)
        self.selection_tool.build_selection_actions()
        self.property_tool.build_property_actions()
        self.overlay_tool.build_overlay_actions()  # overlay of another structure
        self.fragment_tool.build_fragment_actions()  # the user's own fragments
        self.scheme_tool.build_scheme_actions()  # display schemes
        self.view_tool.build_view_actions()  # standard views
        self.structure_tool.build_structure_actions()  # selection by numbers, frames, data of the structure (menus)
        self.calculation_tool.build_calculation_tools()  # «Расчёт» — quick xtb, the steps as data, the modes of atoms
        # «Вид → Ленты белка»; the actions of ProteinTool, kept on the window for the menus
        self.ribbon_action, self.peptide_action = self.protein_tool.ribbon_action, self.protein_tool.peptide_action
        self.coordination_action = self.coordination_tool.action
        self.surface_tool.build_surface_actions()  # orbitals and ESP on the model
        self.viewer.bondMenuRequested.connect(self.model_menu_tool.bond_menu)
        self.viewer.atomMenuRequested.connect(self.model_menu_tool.atom_menu)
        self.build_mode.currentIndexChanged.connect(self.change_build_mode)
        self.build_mode.activated.connect(
            lambda: self.show_periodic_table() if self.build_mode.currentData() == 'atom' else None
        )
        self.element.activated.connect(lambda: self.build_mode.setCurrentIndex(1))
        self.fragment.activated.connect(lambda: self.build_mode.setCurrentIndex(2))
        self.undo_shortcut = QShortcut(QKeySequence.StandardKey.Undo, self)
        self.undo_shortcut.activated.connect(self.undo_geometry)
        self.redo_shortcut = QShortcut(QKeySequence.StandardKey.Redo, self)
        self.redo_shortcut.activated.connect(self.redo_geometry)
        self.change_build_mode()
        self.model_selection_changed([])
        self.update_history_buttons()

    def sync_view_tabs(self):
        """The shown tabs «Молекула | Координаты» follow structure_tabs (texts after a language change)."""
        bar = self.view_tabs
        bar.blockSignals(True)
        while bar.count() > self.structure_tabs.count():
            bar.removeTab(bar.count() - 1)
        for i in range(self.structure_tabs.count()):
            if i < bar.count():
                bar.setTabText(i, self.structure_tabs.tabText(i))
            else:
                bar.addTab(self.structure_tabs.tabText(i))
        bar.setCurrentIndex(self.structure_tabs.currentIndex())
        bar.blockSignals(False)

    def _follow_structure_tab(self, index):
        if self.view_tabs.currentIndex() != index:
            self.view_tabs.blockSignals(True)
            self.view_tabs.setCurrentIndex(index)
            self.view_tabs.blockSignals(False)


