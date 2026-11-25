"""Compass: the actions of the Chemcraft-like menus that Compass did not have.

§1 PURPOSE The menus «Правка», «Вид» and «Инструменты» of Compass hold what Chemcraft has there (docs:
    chemcraftprog.com/help, menus Edit, View, Tools), except what other sections of Azimuth do. This mixin makes the
    QActions of the new operations (modules/compass/chemistry/structure_tools.py) and of the view controls that were
    only buttons; hub/window.py puts them into the menus.
§2 ALGORITHM
    A structure operation takes the structure of the table (table_molecule), computes the new one with structure_tools
    and loads it with edit_structure — one undoable step, the camera kept. Results of a calculation are read-only
    (browsing): the operations that change the structure say so instead. Selections use viewer.set_selection; the
    order of selection matters for the frames (origin, X, the XY plane). Measurements are pinned on the model
    (viewer.pinned: pairs and triples). The camera is copied to the clipboard as JSON ({"azimuth_camera": 1, yaw, pitch,
    roll, zoom, pan, perspective}) and pasted back. The data of the structure are shown in a small window with a «Copy»
    button (plain text for a lab notebook).
§3 APPLICATIONS
    modules/compass/workspace.py (CompassWorkspace mixes it in; build_structure_actions), hub/window.py (menus).
§4 SPECIFICATION
    build_structure_actions(); chem_actions: dict name -> QAction; chem_menus: dict name -> QMenu.
§5 PROCEDURES — below.
§6 NOTES «All bond angles» of a big molecule would cover it with numbers: more than ANGLE_LIMIT (structure_measures.py) angles are refused with
    a hint to select a part. Van der Waals spheres of Chemcraft are not here: they are the model «Заполнение
    пространства» of «Отображение». «Скрыть атомы H»: viewer.hidden_atoms, left out of bond_depth.model_scene.
§7 TESTS
    tests/compass/test_structure_tools.py (the operations), tests/hub/test_hub.py (the menus).
§8' ROBUSTNESS
    Every operation catches ValueError of structure_tools and shows it with self.error; nothing is changed then.
"""

import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMenu,
    QPushButton,
    QTextBrowser,
    QVBoxLayout,
)

from azimuth.core import Z
from azimuth.i18n import tr
from azimuth.ui import smooth
from modules.compass.chemistry import structure_tools as st
from modules.compass.actions import structure_styles as _styles
from modules.compass.actions import structure_editing as _editing
from modules.compass.actions import structure_measures as _measures


class StructureTool:
    """Was the mixin StructureActions of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        '_isotopes',  # Calculation.isotopes kept by the window
        '_report_box',
        'bond_color_actions',  # set_view_option keeps the checks of «Вид → Отображение связей» in step
        'bond_option_actions',
        'bond_width_actions',
        'axes_button',
        'browsing',
        'charge',  # «Проверить структуру», the protons
        'chem_actions',
        'chem_menus',
        'coordinate_tool',
        'current_document',
        'document_title',
        'documents',
        'error',
        'label_mode',
        'model_menu_tool',
        'molecule',
        'notify',
        'overlay_tool',
        'preferences',
        'projection',
        'spin',
        'toggle_axes',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def build_structure_actions(self):
        acts, menus = {}, {}

        def make(key, title, callback, keys=None, checkable=False, tip=None):
            item = QAction(tr(title), self.w.widget)
            # «triggered» gives the state of the item (False) — a checkable item hands it on, any
            # other is called with nothing, so a command with an optional argument (values=None) opens its window
            if checkable:
                item.triggered.connect(lambda checked=False: callback(checked))
            else:
                item.triggered.connect(lambda checked=False: callback())
            if keys is not None:
                item.setShortcut(QKeySequence(keys))
                item.setShortcutContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
                self.w.viewer.addAction(item)
            item.setCheckable(checkable)
            if tip:
                item.setToolTip(tr(tip))
            acts[key] = item
            return item

        # «Правка» → «Выделение»
        make('expand', 'Расширить выделение на шаг', self.expand_selection, 'Ctrl+]',
             tip='Добавить к выделенным атомам связанных с ними соседей')
        make('select_numbers', 'Выделить по номерам…', self.select_by_numbers)
        make('select_box', 'Выделить в диапазоне координат…', self.select_in_box)
        # «Правка» → «Атомы и связи»
        make('set_element', 'Сделать выделенные атомы элементом…', self.set_selected_element)
        make('dummy', 'Точка X в центр выделенных атомов', self.add_dummy_centre,
             tip='Фиктивный атом X — для Z-матрицы, центра цикла или оси')
        make('overlap', 'Убрать перекрывающиеся атомы', self.remove_overlapping,
             tip='Атомы ближе 0,5 Å к другому атому (например, после склейки ячеек)')
        make('rebond', 'Найти связи заново', self.find_bonds_again, tip='Связи по расстояниям, как при открытии файла')
        make('unbond_selected', 'Удалить связи выделенных атомов', self.remove_selected_bonds)
        # «Правка» как в Chemcraft — вся молекула, порядок атомов, все связи, сдвиг и поворот, плоскости, SMILES
        make('whole', 'Выделить молекулу целиком', self.select_whole, 'Ctrl+Shift+]',
             tip='Выделение расширяется до целых молекул, которых оно касается')
        make('order_selected', 'Выделенные атомы — первыми', self.order_selected_first,
             tip='Номера 1, 2, 3… — в порядке выделения (щелчков); остальные — следом. Для фрагмента CDA, Z-матрицы, '
                 'одинаковой нумерации двух файлов')
        make('order_h', 'Водороды — после своих атомов', self.order_hydrogens,
             tip='C1 H2 H3 C4 H5…: каждый водород сразу после атома, с которым связан')
        make('unbond_all', 'Удалить все связи', self.remove_all_bonds,
             tip='Модель без связей; «Найти связи заново» вернёт их по расстояниям')
        make('transform', 'Сдвинуть и повернуть…', self.transform_atoms,
             tip='Выделенные атомы (или все) — повернуть вокруг оси и сдвинуть на вектор')
        make('planes', 'Плоскости групп атомов…', self.show_planes,
             tip='Средняя плоскость группы атомов, отклонения от неё, угол между двумя плоскостями (стэкинг колец)')
        make('copy_smiles', 'Копировать SMILES', self.copy_smiles, tip='SMILES структуры — в буфер обмена')
        # «Правка → Векторы и плоскости» (Operations with vectors and planes of Chemcraft)
        make('guide_vector', 'Вектор между выделенными атомами', lambda: self.add_guide('vector'),
             tip='Стрелка от первого выделенного атома ко второму')
        make('guide_normal', 'Нормаль к плоскости выделенных атомов', lambda: self.add_guide('normal'),
             tip='Стрелка 1,5 Å из центра средней плоскости трёх или больше атомов')
        make('guide_plane', 'Плоскость через выделенные атомы', lambda: self.add_guide('plane'),
             tip='Полупрозрачная средняя плоскость трёх или больше атомов (например, кольца)')
        make('guide_angles', 'Углы между векторами и плоскостями…', self.show_guide_angles)
        make('guide_text', 'Векторы и плоскости текстом…', self.edit_guides_text,
             tip='Список строкой на объект: «вектор 1 2», «вектор 0 0 0 1 0 0» (координаты, Å), «нормаль 1-6», '
                 '«плоскость 1-6»')
        make('guide_clear', 'Убрать векторы и плоскости', self.clear_guides)
        make('guide_style', 'Стиль векторов и плоскостей…', self.guide_style)
        guides_menu = smooth(QMenu(tr('Векторы и плоскости'), self.w.widget))
        for key in ('guide_vector', 'guide_normal', 'guide_plane', None, 'guide_angles', 'guide_text', 'guide_style',
                    None, 'guide_clear'):
            guides_menu.addSeparator() if key is None else guides_menu.addAction(acts[key])
        menus['guides'] = guides_menu
        order = smooth(QMenu(tr('Порядок атомов'), self.w.widget))
        order.addAction(acts['order_selected'])
        order.addAction(acts['order_h'])
        menus['order'] = order
        # «Правка» → «Система координат»
        make('origin', 'Начало координат — в выделенный атом', self.origin_to_atom)
        make('axes3', 'Оси по трём выделенным атомам', self.axes_to_three,
             tip='Первый атом — начало, ось X — ко второму, третий — в плоскости XY')
        for axis in 'xyz':
            make('along_' + axis, f'Два выделенных атома вдоль оси {axis.upper()}',
                 lambda checked=False, a=axis: self.two_along(a))
        make('principal', 'Повернуть к главным осям инерции', self.to_principal_axes,
             tip='Начало — в центре масс, оси X, Y, Z — вдоль главных осей A, B, C')
        make('invert_xyz', 'Инвертировать координаты (r → −r)', self.invert_coordinates)
        make('shake', 'Небольшое случайное смещение атомов', self.shake_atoms,
             tip='До 0,01 Å — чтобы оптимизация ушла с симметричной седловой точки')
        coords = smooth(QMenu(tr('Система координат'), self.w.widget))
        for key in ('origin', 'axes3', None, 'along_x', 'along_y', 'along_z', None, 'principal', 'invert_xyz', 'shake'):
            coords.addSeparator() if key is None else coords.addAction(acts[key])
        menus['coordinates'] = coords
        # «Вид»
        make('perspective', 'Перспектива', lambda on: self.w.projection.setCurrentIndex(1 if on else 0), checkable=True)
        # the two projections of the field as two
        # items, one of them checked (the choice «Isometry / Perspective» of the field)
        make('isometry', 'Изометрия', lambda on: self.w.projection.setCurrentIndex(0 if on else 1), checkable=True)
        from PySide6.QtGui import QActionGroup

        projections = QActionGroup(self.w.widget)
        projections.setExclusive(True)
        for key in ('isometry', 'perspective'):
            projections.addAction(acts[key])
        acts['isometry'].setChecked(True)
        make('center', 'Центровать', self.w.viewer.center_view)
        make('best', 'Лучший ракурс', self.w.viewer.best_view)
        make('axes', 'Оси X, Y, Z', lambda on: (self.w.axes_button.setChecked(on), self.w.toggle_axes()), checkable=True)
        make('camera_copy', 'Копировать положение камеры', self.copy_camera)
        make('camera_paste', 'Вставить положение камеры', self.paste_camera)
        # «Отображение» → «Скрыть атомы H» (every display mode and both engines; a selected H stays shown)
        make('hide_h', 'Скрыть атомы H', self.set_hydrogens_hidden, checkable=True,
             tip='Водороды не рисуются; выделенные остаются. Структура и расчёт их сохраняют')
        make('copy_image', 'Копировать рисунок', self.copy_picture, tip='Модель — в буфер обмена, для письма или слайда')
        labels = smooth(QMenu(tr('Подписи атомов'), self.w.widget))
        for title, key in ((tr('Элемент · C'), 'element'), (tr('Номер · 1'), 'number'), (tr('Элемент и номер · C1'), 'both'),
                           (tr('Номер в элементе · C1, H1'), 'group'), (tr('Без подписей'), 'none')):
            item = labels.addAction(title)
            item.setCheckable(True)
            item.setData(key)
            item.triggered.connect(lambda checked=False, k=key: self.w.label_mode.setCurrentIndex(max(0, self.w.label_mode.findData(k))))
        # the labels of the bonds, of the selection only, their style (View → Labels on atoms/bonds of Chemcraft)
        labels.addSeparator()
        make('bond_numbers', 'Номера связей', lambda on: self.set_bond_labels('number' if on else None), checkable=True)
        make('bond_orders', 'Порядки связей', lambda on: self.set_bond_labels('order' if on else None), checkable=True,
             tip='1, 2, 3 или 1.5 (ароматическая) — по валентностям, как в Компасе')
        make('labels_selected', 'Подписи только у выделенных', self.set_labels_selected_only, checkable=True)
        make('label_style', 'Стиль подписей…', self.label_style)
        for key in ('bond_numbers', 'bond_orders', 'labels_selected', None, 'label_style'):
            labels.addSeparator() if key is None else labels.addAction(acts[key])
        modes = ('element', 'number', 'both', 'group', 'none')

        def shown_labels():
            for a in labels.actions():
                if a.data() in modes:
                    a.setChecked(a.data() == self.w.viewer.label_mode)
            acts['bond_numbers'].setChecked(self.w.viewer.bond_labels == 'number')
            acts['bond_orders'].setChecked(self.w.viewer.bond_labels == 'order')
            acts['labels_selected'].setChecked(self.w.viewer.labels_selected_only)

        labels.aboutToShow.connect(shown_labels)
        menus['labels'] = labels
        # the rest of «Вид» of Chemcraft — the centre of rotation, the camera by numbers, the axes on the model,
        # the van der Waals spheres, hidden atoms, the style of the measurements
        make('pivot', 'Центр вращения — выделенные атомы', self.rotate_about_selection,
             tip='Модель вращается вокруг центра выделенных атомов; «Центровать» вернёт центр молекулы')
        make('camera_set', 'Положение камеры…', self.set_camera_numbers,
             tip='Углы поворота и масштаб числами — один и тот же ракурс для разных структур')
        axes_menu = smooth(QMenu(tr('Где оси'), self.w.widget))
        for key, title in (('corner', 'В углу поля'), ('centre', 'Из центра молекулы'), ('origin', 'Из начала координат')):
            item = make('axes_' + key, title, lambda checked=False, k=key: self.set_axes_place(k), checkable=True)
            axes_menu.addAction(item)
        axes_menu.aboutToShow.connect(lambda: [acts['axes_' + k].setChecked(self.w.viewer.axes_place == k)
                                               for k in ('corner', 'centre', 'origin')])
        menus['axes'] = axes_menu
        make('vdw', 'Сферы Ван-дер-Ваальса', self.set_vdw_spheres, checkable=True,
             tip='Полупрозрачные сферы радиусов Бонди поверх модели — видны контакты и пустоты')
        make('hide_selected', 'Скрыть выделенные атомы', self.hide_selected_atoms,
             tip='Атомы не рисуются, но остаются в структуре и расчёте')
        make('show_all', 'Показать все атомы', self.show_all_atoms)  # no Ctrl+H: on a Mac ⌘H hides the program
        make('hide_dummies', 'Скрыть фиктивные атомы X', self.set_dummies_hidden, checkable=True)
        make('measure_style', 'Стиль измерений…', self.measure_style)
        make('all_distances', 'Все расстояния между выделенными атомами', self.pin_distances)
        make('all_angles', 'Все валентные углы', self.pin_angles, tip='Выделенной части или всей молекулы')
        make('clear_pins', 'Убрать измерения с модели', self.clear_pins)
        # «Инструменты»
        make('inertia', 'Моменты инерции и вращательные постоянные…', self.show_inertia)
        make('statistics', 'Статистика атомов и связей…', self.show_statistics)
        make('masses', 'Масса молекулы…', self.show_masses, tip='Точная (моноизотопная) и средняя молекулярная масса')
        # the tools of Chemcraft that belong to a structure (the others went to Spectrum)
        make('internal', 'Таблица внутренних координат…', self.show_internal_coordinates,
             tip='Все длины связей, валентные и двугранные углы; сохранить CSV')
        make('size', 'Объём и площадь поверхности…', self.show_molecular_size,
             tip='Ван-дер-ваальсов объём, площадь поверхности, доступная растворителю площадь, эффективный диаметр')
        # the check of the structure, the explicit solvation, the protons
        make('check_structure', 'Проверить структуру…', self.check_structure,
             tip='Заряд и мультиплетность, слишком близкие атомы, валентности, несвязанные части — до расчёта')
        make('solvate', 'Окружить растворителем…', self.solvate_dialog,
             tip='Явная сольватация: молекулы растворителя вокруг структуры, без наложений')
        make('unsolvate', 'Убрать растворитель', self.remove_solvent,
             tip='Молекулы растворителя, поставленные вокруг структуры (вода, метанол, ДМСО …), — прочь')
        make('isotopes', 'Изотопы выделенных атомов…', self.isotope_dialog,
             tip='D вместо H, ¹³C, ¹⁸O … — для изотопных сдвигов частот (ORCA: масса атома во входном файле)')
        make('proton_add', 'Добавить протон к выделенному атому (+1)', self.add_proton)
        make('proton_remove', 'Снять протон (−1)', self.remove_proton,
             tip='Выделенный водород или водород выделенного атома')
        make('proton_move', 'Перенести протон к выделенному атому', self.move_proton,
             tip='Выделите водород и атом — таутомер, заряд не меняется')
        protons = smooth(QMenu(tr('Протоны'), self.w.widget))
        for key in ('proton_add', 'proton_remove', None, 'proton_move'):
            protons.addSeparator() if key is None else protons.addAction(acts[key])
        menus['protons'] = protons
        compare_tabs = smooth(QMenu(tr('Сравнить с вкладкой'), self.w.widget))
        compare_tabs.setToolTipsVisible(True)
        compare_tabs.aboutToShow.connect(lambda: self.fill_compare_tabs(compare_tabs))
        menus['compare_tabs'] = compare_tabs
        fragments = smooth(QMenu(tr('Фрагменты структуры'), self.w.widget))
        fragments.aboutToShow.connect(lambda: self.fill_fragments_menu(fragments))
        menus['fragments'] = fragments
        self.w.chem_actions, self.w.chem_menus = acts, menus

    # -- helpers ----------------------------------------------------------------------------------------------------
    def _change(self, function, message='', selection=None):
        """Apply function(structure) -> structure as one undoable edit; a read-only result or an error is said."""
        if self.w.browsing:
            self.w.notify(tr('Это результат расчёта — откройте его как новую молекулу, чтобы менять.'))
            return False
        if not self.w.molecule.atoms:
            return False
        try:
            result = function(self.w.coordinate_tool.table_molecule())
        except (ValueError, KeyError, IndexError) as exc:
            self.w.error(exc)
            return False
        self.w.model_menu_tool.edit_structure(result, message)
        if selection is not None:
            self.w.viewer.set_selection(selection)
        return True

    def _chosen(self, least, what):
        chosen = list(self.w.viewer.selected)
        if len(chosen) < least:
            self.w.notify(tr(f'Выделите {what}.'))
            return None
        return chosen

    def _report(self, title, text, extra=()):
        """A small window with plain text and «Копировать» (for a lab notebook); extra — [(title, callback)] buttons
        («Сохранить CSV…»)."""
        from azimuth.ui import label

        box = QDialog(self.w.widget)
        box.setWindowTitle(title)
        lay = QVBoxLayout(box)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.setSpacing(10)
        lay.addWidget(label(title, 'cardtitle'))  # a heading, and the window as tall as its text
        view = QTextBrowser()
        view.setPlainText(text)
        view.setFrameShape(QFrame.Shape.NoFrame)
        view.document().setTextWidth(440)
        view.setMinimumWidth(460)
        view.setFixedHeight(min(420, int(view.document().size().height()) + 16))
        lay.addWidget(view)
        row = QHBoxLayout()
        copy = QPushButton(tr('Копировать'))
        def copy_text():
            from azimuth.ui import copied

            QApplication.clipboard().setText(text)
            copied(box, title, copy)  # said

        copy.clicked.connect(copy_text)
        close = QPushButton(tr('Закрыть'))
        close.clicked.connect(box.accept)
        row.addWidget(copy)
        for name, callback in extra:
            more = QPushButton(name)
            more.clicked.connect(lambda checked=False, c=callback: c())
            row.addWidget(more)
        row.addStretch(1)
        row.addWidget(close)
        lay.addLayout(row)
        self.w._report_box = box
        from azimuth.ui import open_window

        open_window(box)  # a window with its title, not a sheet
        return box

    # -- selection ---------------------------------------------------------------------------------------------------
    def expand_selection(self):
        if self.w.molecule.atoms:
            self.w.viewer.set_selection(st.expand(self.w.molecule, self.w.viewer.selected or []))

    def select_by_numbers(self):
        if not self.w.molecule.atoms:
            return
        symbols = [a.symbol for a in self.w.molecule.atoms]  # «C1–C5, O8» as well as «1-5, 8»
        text, ok = QInputDialog.getText(self.w.widget, tr('Выделить по номерам'),
                                        tr(f'Атомы (1–{len(self.w.molecule.atoms)}), например 1-5, 8, 10 или C1–C5, O8, H:'),
                                        QLineEdit.EchoMode.Normal, st.numbers_text(self.w.viewer.selected, symbols))
        if not ok:
            return
        try:
            self.w.viewer.set_selection(st.parse_numbers(text, len(self.w.molecule.atoms), symbols))
        except ValueError as exc:
            self.w.error(exc)

    def select_in_box(self):
        if not self.w.molecule.atoms:
            return
        box = QDialog(self.w.widget)
        box.setWindowTitle(tr('Выделить в диапазоне координат'))
        form = QFormLayout(box)
        form.addRow(QLabel(tr('Пустое поле — без ограничения. Ангстремы.')))
        fields = []
        for axis in 'XYZ':
            lo, hi = QLineEdit(), QLineEdit()
            lo.setPlaceholderText(tr('от'))
            hi.setPlaceholderText(tr('до'))
            row = QHBoxLayout()
            row.addWidget(lo)
            row.addWidget(hi)
            form.addRow(axis, row)
            fields.append((lo, hi))
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.rejected.connect(box.reject)

        def number(edit):
            t = edit.text().strip().replace(',', '.')
            return float(t) if t else None

        def accept():
            try:
                lo = tuple(number(a) for a, _ in fields)
                hi = tuple(number(b) for _, b in fields)
            except ValueError:
                self.w.notify(tr('Границы — числа в ангстремах.'))
                return
            found = st.in_box(self.w.molecule, lo, hi)
            self.w.viewer.set_selection(found)
            self.w.notify(tr(f'Выделено атомов: {len(found)}.'), 5000)
            box.accept()

        buttons.accepted.connect(accept)
        self._box_dialog = box
        from azimuth.ui import open_window

        open_window(box)  # a window with its title, not a sheet

    # -- atoms and bonds ---------------------------------------------------------------------------------------------
    def set_selected_element(self):
        chosen = self._chosen(1, tr('атомы, которые заменить'))
        if chosen is None:
            return
        symbol, ok = QInputDialog.getText(self.w.widget, tr('Сменить элемент'), tr('Символ элемента (например, N, Cl, Si):'))
        symbol = (symbol or '').strip()
        symbol = symbol[:1].upper() + symbol[1:].lower()
        if not ok or not symbol:
            return
        if symbol not in Z:
            self.w.notify(tr(f'Нет такого элемента: {symbol}.'))
            return
        self._change(lambda m: st.with_element(m, chosen, symbol), selection=chosen)

    def add_dummy_centre(self):
        chosen = self._chosen(1, tr('атомы, в центр которых поставить точку X'))
        if chosen is None:
            return
        holder = {}

        def go(m):
            result, k = st.with_dummy_at_centre(m, chosen)
            holder['k'] = k
            return result

        if self._change(go):
            self.w.viewer.set_selection([holder['k']])

    def remove_overlapping(self):
        found = st.overlapping(self.w.molecule)
        if not found:
            self.w.notify(tr('Перекрывающихся атомов нет.'), 5000)
            return
        self._change(lambda m: st.without(m, found), tr(f'Убрано атомов: {len(found)}.'))

    def find_bonds_again(self):
        self._change(st.rebonded, tr('Связи найдены заново по расстояниям.'))

    def remove_selected_bonds(self):
        chosen = self._chosen(1, tr('атомы'))
        if chosen is not None:
            self._change(lambda m: st.without_bonds_of(m, chosen), selection=chosen)

    # -- frames of coordinates ------------------------------------------------------------------------------------------
    def origin_to_atom(self):
        chosen = self._chosen(1, tr('атом — новое начало координат'))
        if chosen is not None:
            self._change(lambda m: st.origin_at(m, chosen[0]), selection=chosen)

    def axes_to_three(self):
        chosen = self._chosen(3, tr('три атома: начало, направление X и атом в плоскости XY'))
        if chosen is not None:
            self._change(lambda m: st.axes_on(m, *chosen[:3]), selection=chosen)

    def two_along(self, axis):
        chosen = self._chosen(2, tr('два атома'))
        if chosen is not None:
            self._change(lambda m: st.along(m, chosen[0], chosen[1], axis), selection=chosen)

    def to_principal_axes(self):
        self._change(st.principal_frame, tr('Начало — в центре масс, оси — главные оси инерции.'))

    def invert_coordinates(self):
        self._change(st.inverted)

    def shake_atoms(self):
        self._change(lambda m: st.shaken(m, 0.01), tr('Атомы сдвинуты случайно, не больше чем на 0,01 Å.'))

    # -- view -------------------------------------------------------------------------------------------------------------
    def copy_camera(self):
        v = self.w.viewer
        data = {'azimuth_camera': 1, 'yaw': v.yaw, 'pitch': v.pitch, 'roll': v.roll, 'zoom': v.zoom,
                'pan': [v.pan.x(), v.pan.y()], 'perspective': bool(v.perspective)}
        QApplication.clipboard().setText(json.dumps(data))
        self.w.notify(tr('Положение камеры скопировано.'), 4000)

    def paste_camera(self):
        try:
            data = json.loads(QApplication.clipboard().text())
            assert isinstance(data, dict) and data.get('azimuth_camera') == 1
            v = self.w.viewer
            v.yaw, v.pitch, v.roll, v.zoom = (float(data[k]) for k in ('yaw', 'pitch', 'roll', 'zoom'))
            v.pan.setX(float(data['pan'][0]))
            v.pan.setY(float(data['pan'][1]))
            self.w.projection.setCurrentIndex(1 if data.get('perspective') else 0)
            v.update()
        except (ValueError, KeyError, TypeError, AssertionError, IndexError):
            self.w.notify(tr('В буфере обмена нет положения камеры Компаса.'))

    def set_hydrogens_hidden(self, on):
        self.w.viewer.hide_hydrogens = bool(on)
        self.w.chem_actions['hide_h'].setChecked(bool(on))
        hidden = len(self.w.viewer.hidden_atoms())
        if on and hidden:
            self.w.notify(tr(f'Скрыто атомов H: {hidden}. Выделенные водороды видны.'), 5000)
        self.w.viewer.update()

    # -- «Вид» -------------------------------------------------------------------------------------------
    def set_bond_labels(self, kind):
        self.w.viewer.bond_labels = kind
        self.w.chem_actions['bond_numbers'].setChecked(kind == 'number')
        self.w.chem_actions['bond_orders'].setChecked(kind == 'order')
        self.w.viewer.update()
        return kind

    def set_labels_selected_only(self, on):
        self.w.viewer.labels_selected_only = bool(on)
        self.w.viewer.update()

    def set_vdw_spheres(self, on):
        self.w.viewer.show_vdw = bool(on)
        self.w.chem_actions['vdw'].setChecked(bool(on))
        self.w.viewer.update()

    def set_axes_place(self, place):
        """«Где оси»: in the corner of the field, or on the model from its centre or from the origin (the axes on)."""
        self.w.viewer.axes_place = place
        if not self.w.viewer.show_axes:
            self.w.axes_button.setChecked(True)
            self.w.toggle_axes()
        self.w.viewer.update()
        return place

    def rotate_about_selection(self):
        chosen = self._chosen(1, tr('атомы — центр вращения'))
        if chosen is None:
            return None
        atoms = self.w.molecule.atoms
        point = tuple(sum(atoms[i].position[k] for i in chosen) / len(chosen) for k in range(3))
        self.w.viewer.rotate_about(point)
        return point

    def hide_selected_atoms(self):
        chosen = self._chosen(1, tr('атомы, которые скрыть'))
        if chosen is None:
            return 0
        self.w.viewer.user_hidden = frozenset(self.w.viewer.user_hidden) | frozenset(chosen)
        self.w.viewer.set_selection([])
        self.w.notify(tr('Скрыто атомов: ') + str(len(self.w.viewer.user_hidden)) + tr('. Вернуть — «Вид → Показать все атомы».'),
                    6000)
        return len(self.w.viewer.user_hidden)

    def show_all_atoms(self):
        self.w.viewer.user_hidden = frozenset()
        self.set_dummies_hidden(False)
        if self.w.viewer.hide_hydrogens:
            self.set_hydrogens_hidden(False)
        self.w.viewer.update()

    def set_dummies_hidden(self, on):
        self.w.viewer.hide_dummies = bool(on)
        self.w.chem_actions['hide_dummies'].setChecked(bool(on))
        self.w.viewer.update()

    _styles_window = _styles._styles_window
    check_structure = _editing.check_structure
    solvate_dialog = _editing.solvate_dialog
    remove_solvent = _editing.remove_solvent
    isotope_dialog = _editing.isotope_dialog
    own_isotope_mass = _editing.own_isotope_mass
    set_isotopes = _editing.set_isotopes
    _one_chosen = _editing._one_chosen
    add_proton = _editing.add_proton
    remove_proton = _editing.remove_proton
    move_proton = _editing.move_proton
    _theme_ink = _styles._theme_ink
    _keep_styles = _styles._keep_styles

    LABEL_STYLE = ('label_scale', 'label_font', 'label_bold', 'label_italic', 'label_color', 'label_outline',
                   'label_place')
    MEASURE_STYLE = ('measure_size', 'measure_decimals', 'measure_font', 'measure_bold', 'measure_italic',
                     'measure_color', 'measure_line_color', 'measure_plate')

    BOND_STYLE = ('bond_uniform_color', 'bond_aromatic_style', 'bond_partial_color', 'bond_long_dashed',
                  'bond_long_factor', 'hbond_color', 'hbond_width', 'hbond_style')

    set_view_option = _styles.set_view_option
    bond_style = _styles.bond_style
    label_style = _styles.label_style
    measure_style = _styles.measure_style
    set_camera_numbers = _styles.set_camera_numbers

    def copy_picture(self):
        if not self.w.molecule.atoms:
            return
        QApplication.clipboard().setPixmap(self.w.viewer.render_image(2, self.w.viewer.transparent))
        self.w.notify(tr('Рисунок скопирован.'), 4000)

    pin_distances = _measures.pin_distances
    pin_angles = _measures.pin_angles
    _pin = _measures._pin
    clear_pins = _measures.clear_pins
    show_inertia = _measures.show_inertia

    # -- 0.91.76 --------------------------------------------------------------------------------------------------
    def select_whole(self):
        if self.w.molecule.atoms:
            if not self.w.viewer.selected:
                self.w.notify(tr('Выделите хотя бы один атом молекулы.'))
                return
            self.w.viewer.set_selection(st.whole(self.w.molecule, self.w.viewer.selected))

    def order_selected_first(self):
        chosen = self._chosen(1, tr('атомы в том порядке, в каком им дать номера 1, 2, 3…'))
        if chosen is None:
            return False
        done = self._change(lambda m: st.selected_first(m, chosen)[0],
                            tr('Выделенные атомы теперь первые: ') + str(len(chosen)) + '.',
                            selection=list(range(len(chosen))))
        return done

    def order_hydrogens(self):
        return self._change(lambda m: st.hydrogens_after(m)[0], tr('Водороды стоят после своих атомов.'))

    def remove_all_bonds(self):
        return self._change(st.without_bonds, tr('Все связи удалены. «Найти связи заново» вернёт их.'))

    def copy_smiles(self):
        from modules.compass.chemistry import pubchem

        if not self.w.molecule.atoms:
            return None
        text = pubchem.to_smiles(self.w.molecule)
        QApplication.clipboard().setText(text)
        self.w.notify(tr('Скопирован SMILES: ') + text, 6000)
        return text

    transform_atoms = _measures.transform_atoms
    planes_text = _measures.planes_text
    show_planes = _measures.show_planes
    add_guide = _measures.add_guide

    GUIDE_STYLE = ('guide_vector_color', 'guide_normal_color', 'guide_plane_color', 'guide_vector_show',
                   'guide_normal_show', 'guide_plane_show', 'guide_width', 'guide_plane_opacity', 'guide_plane_edge',
                   'guide_numbers', 'guide_normal_length', 'guide_plane_margin')

    guide_style = _measures.guide_style
    clear_guides = _measures.clear_guides
    guide_angles_text = _measures.guide_angles_text
    show_guide_angles = _measures.show_guide_angles
    edit_guides_text = _measures.edit_guides_text
    internal_rows = _measures.internal_rows
    save_internal_csv = _measures.save_internal_csv
    show_internal_coordinates = _measures.show_internal_coordinates
    molecular_size_text = _measures.molecular_size_text
    show_molecular_size = _measures.show_molecular_size

    def fill_compare_tabs(self, menu):
        """«Сравнить с вкладкой»: the other tabs with a structure; one of them overlaid on the model with its RMSD."""
        menu.clear()
        here = self.w.current_document if getattr(self.w, 'documents', None) else -1
        found = 0
        for k, d in enumerate(getattr(self.w, 'documents', [])):
            molecule = d.molecule
            if k == here or molecule is None or not molecule.atoms:
                continue
            title = self.w.document_title(k)
            item = menu.addAction(title)
            item.setToolTip(tr('Наложить на модель и посчитать RMSD (атомы сопоставляются сами)'))
            item.triggered.connect(lambda checked=False, m=molecule, t=title: self.compare_with_tab(m, t))
            found += 1
        if not found:
            menu.addAction(tr('Других вкладок со структурой нет')).setEnabled(False)
        return found

    def compare_with_tab(self, molecule, title):
        return self.w.overlay_tool.set_compare(molecule, tr('вкладка «') + title + '»')

    show_statistics = _measures.show_statistics
    show_masses = _measures.show_masses

    def fill_fragments_menu(self, menu):
        menu.clear()
        parts = st.fragments(self.w.molecule) if self.w.molecule.atoms else []
        if len(parts) < 2:
            item = menu.addAction(tr('Структура цельная — один фрагмент'))
            item.setEnabled(False)
            return
        for n, part in enumerate(parts, start=1):
            formula = st.Molecule('', tuple(self.w.molecule.atoms[i] for i in part)).formula
            menu.addAction(tr(f'Фрагмент {n}: {formula} — атомы {st.numbers_text(part)}')).triggered.connect(
                lambda checked=False, p=part: self.w.viewer.set_selection(p))
