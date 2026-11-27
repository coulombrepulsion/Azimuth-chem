"""«Файл → Настройки…»: one window for the preferences of the whole program.

§1 PURPOSE
    The choices that were scattered over the menus (the style of the CSV tables in «Поверхность на модели»,
    the hydrogens of files without H in a menu of the old window, the folder of the calculations behind an icon of
    Sextant, the grid and the program of Multiwfn) in one window, applied at once (no «OK»), kept in the settings of
    the program as before (the same keys: nothing is lost on the update).
§4 SPECIFICATION SettingsDialog(studio, hub=None, focus=None): sections «Оформление» (language — with the hub only —,
    theme and check_updates — azimuth/updates.py CHECK_KEY), «Файлы» (hydrogens), «Таблицы анализа (CSV)» (separator, decimal, sample), «Расчёты» (folder), «Multiwfn»
    (grid, program), «Ошибки» (the folder of the logs, report_button, logs_button); as Tools → Preferences of Chemcraft
    (values in azimuth/defaults.py, the open windows follow by studio.apply_default): «Связи и шаги» (bond_factor,
    bond_order, common_orientation), «Снимки» (picture_scale, picture_transparent, picture_crop), «Спектры» (ir_style,
    ir_width, ir_scale_on, uv_fwhm); each with reset_buttons[section] «По умолчанию»; the icon of each section at its heading (nav
    {section: QToolButton}, the glyphs of SECTION_ICONS; a row of them over the window till 0.222.26). «Вид модели» (start_scheme — '' «как в
    прошлый раз» or a scheme; quick_atoms), «Единицы» (coordinate_unit, energy_unit), «Программы» (program_paths {kind:
    QLabel}, program_buttons {kind: (Указать…, Искать самой)}; the keys programs/<kind> of Sextant), «Все настройки»
    (export_settings(path), import_settings(path), reset_all(ask) — the settings as a JSON file without the secret keys
    of crash_report.SECRET; all_note tells what happened). focus ∈ SECTIONS scrolls to it and marks it. Widgets:
    language, theme, hydrogens, separator, decimal, sample, jobs_folder, jobs_button, projects_folder, projects_button,
    grid, multiwfn_path, multiwfn_button, boxes {section: QGroupBox}. Keys: hub_language, theme (by the hub),
    hydrogens_on_open, csv_style (field_tables.valid_style), jobs_folder, multiwfn_grid, multiwfn_program.
§7 TESTS
    tests/test_gui.py::test_settings_window.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog, QDoubleSpinBox, QFormLayout, QGroupBox, QHBoxLayout,
                               QLabel, QScrollArea, QSpinBox, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import button, label

SECTIONS = ('look', 'files', 'model', 'view', 'pictures', 'spectra', 'units', 'tables', 'jobs', 'programs', 'multiwfn',
            'errors', 'all')
SECTION_ICONS = {'look': ('palette', 'Оформление'), 'files': ('file-open', 'Файлы'),
                 'model': ('bond-length', 'Связи и шаги'), 'pictures': ('picture-scale', 'Снимки'),
                 'spectra': ('band-width', 'Спектры'), 'tables': ('table', 'Таблицы анализа (CSV)'),
                 'jobs': ('queue', 'Расчёты'), 'multiwfn': ('surface', 'Multiwfn'), 'errors': ('bug', 'Ошибки'),
                 'view': ('model-look', 'Вид модели'), 'units': ('units', 'Единицы'),
                 'programs': ('programs', 'Программы'), 'all': ('settings-file', 'Все настройки')}
RESET = {'model': ('bond_factor', 'bond_order_min', 'common_orientation'),
         'pictures': ('picture_scale', 'picture_transparent', 'picture_crop'),
         'spectra': ('ir_style', 'ir_width', 'ir_scale_on', 'uv_fwhm'),
         'units': ('coordinate_unit', 'energy_unit'), 'view': ('quick_atoms',)}
EXPORT_MARK = 'azimuth-settings'  # the first key of a file of «Сохранить в файл…»
COORDINATE_UNITS = (('angstrom', 'Ангстремы (Å)'), ('bohr', 'Боры (a₀)'))
ENERGY_UNITS = (('kcal', 'ккал/моль'), ('kj', 'кДж/моль'), ('ev', 'эВ'))
LANGUAGE_NAMES = (('ru', 'Русский'), ('en', 'English'), ('zh', '中文'))


SCROLL_ROOM = 16  # px between the cards and the right edge — the scroll bar is there
HEADING_ICON = 22  # px, the icon of a section before its heading (18 until 0.249.4: the glyph is 20 of 24 now, the gold star in its corner)


class SettingsDialog(QDialog):
    def __init__(self, studio, hub=None, focus=None):
        super().__init__(studio.window() if hub is None else hub)
        self.studio, self.hub = studio, hub
        self.setWindowTitle(tr('Настройки'))
        self.setObjectName('settingsDialog')
        outer = QVBoxLayout(self)
        note = label(tr('Изменения настроек сохраняются до следующего раза.'), 'subtitle')
        note.setWordWrap(True)  # at the bottom, next to «Закрыть» (the owner, 2026-11-23)
        self.note = note
        # the icon of each section stands at its heading (_box), not in a row over the window (the owner, 2026-11-23:
        # «перенеси иконки сверху настроек к заголовкам соответствующим»)
        self.nav = {}
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        body = QWidget()
        column = QVBoxLayout(body)
        # room on the right for the scroll bar: on macOS it is drawn over the content and lay on the right edge of the
        # cards (the owner, 2026-11-23)
        column.setContentsMargins(0, 0, SCROLL_ROOM, 0)
        self.boxes = {}
        self.reset_buttons = {}
        self._look(column)
        self._files(column)
        self._model(column)
        self._view(column)
        self._pictures(column)
        self._spectra(column)
        self._units(column)
        self._tables(column)
        self._jobs(column)
        self._programs(column)
        self._multiwfn(column)
        self._errors(column)
        self._all(column)
        column.addStretch(1)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)
        # the wheel over a list
        # or a number of the window only scrolls the window — it changed the field under the pointer (Qt does so even
        # without the focus): scrolling down over «Схема при запуске» chose its last scheme, «Презентация», and kept it;
        # the factor of the bonds and the threshold of the bond orders were moved the same way. A field takes the wheel
        # only after a click on it (it has the focus then).
        from PySide6.QtWidgets import QAbstractSpinBox

        from azimuth.ui import center_combo

        for field in body.findChildren(QComboBox) + body.findChildren(QAbstractSpinBox):
            field.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
            field.installEventFilter(self)
            # the values in the middle of their fields here too, not only where the finishing touches of the program
            # are installed (azimuth/polish.py; the owner, 2026-11-23: «значения не в центре полей, как и слово никогда»)
            if isinstance(field, QAbstractSpinBox):
                field.setAlignment(Qt.AlignmentFlag.AlignCenter)
            elif not field.isEditable():
                center_combo(field)
        row = QHBoxLayout()
        row.addWidget(note, 1)
        row.addWidget(button(tr('Закрыть'), self.accept))  # what closes is white
        outer.addLayout(row)
        # as wide as its widest section (and the scroll bar), no scrolling sideways; no wider than the
        # screen; the height as before
        body.ensurePolished()
        body.adjustSize()
        bar = self.scroll.verticalScrollBar().sizeHint().width()
        margins = outer.contentsMargins()
        wide = body.sizeHint().width() + bar + margins.left() + margins.right() + 8
        wide = max(560, wide)
        screen = self.screen()
        if screen is not None:
            wide = min(wide, screen.availableGeometry().width() - 40)
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff if screen is None or
                                                 wide < screen.availableGeometry().width() - 40 else
                                                 Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.resize(wide, 620)
        if focus in self.boxes:
            self.show_section(focus)

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QCoreApplication, QEvent
        from PySide6.QtWidgets import QAbstractSpinBox

        # a list never takes the wheel, even with the focus (azimuth/app.py _quiet_wheel_style)
        if event.type() == QEvent.Type.Wheel and (isinstance(watched, QComboBox) or (
                isinstance(watched, QAbstractSpinBox) and not watched.hasFocus())):
            QCoreApplication.sendEvent(self.scroll.viewport(), event)  # the window scrolls, the field stays
            return True
        return super().eventFilter(watched, event)

    # -- sections -------------------------------------------------------------------------------------------------------
    def _box(self, key, title):
        box = QGroupBox(tr(title))
        glyph = SECTION_ICONS.get(key, (None,))[0]
        if glyph:  # the icon of the section before its heading; the heading moves right to make room for it
            from PySide6.QtCore import QSize
            from PySide6.QtWidgets import QToolButton

            from azimuth.icons import icon

            mark = QToolButton(box)
            mark.setObjectName('sectionMark')
            mark.setIcon(icon(glyph, spark=True))  # in the colour of the theme, a gold star at its corner (0.249.4)
            mark.setIconSize(QSize(HEADING_ICON, HEADING_ICON))
            mark.setAutoRaise(True)
            mark.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            mark.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            mark.setStyleSheet('QToolButton#sectionMark {border: none; background: transparent; padding: 0;}')
            mark.setGeometry(2, 0, HEADING_ICON + 2, HEADING_ICON + 2)
            mark.setProperty('quail_icon', glyph)
            box.setStyleSheet(f'QGroupBox::title {{padding-left: {HEADING_ICON + 8}px;}}')
            self.nav[key] = mark
        form = QFormLayout(box)
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.boxes[key] = box
        return box, form

    def _look(self, column):
        box, form = self._box('look', 'Оформление')
        self.language = QComboBox()
        for code, name in LANGUAGE_NAMES:
            self.language.addItem(name, code)
        current = getattr(self.hub, 'language', 'ru')
        self.language.setCurrentIndex(max(0, self.language.findData(current)))
        self.language.currentIndexChanged.connect(self.set_language)
        self.language.setEnabled(self.hub is not None)
        form.addRow(tr('Язык'), self.language)
        self.theme = QComboBox()
        self.theme.addItems([tr('Светлая тема'), tr('Тёмная тема'), tr('Как в системе')])  # the third
        self.theme.setItemData(2, tr('Светлая или тёмная — как во внешнем виде системы, и меняется вместе с ним'),
                               Qt.ItemDataRole.ToolTipRole)
        follows = getattr(self.studio, 'follows_system_theme', lambda: False)()
        self.theme.setCurrentIndex(2 if follows else (self.studio.theme.currentIndex() if hasattr(self.studio, 'theme') else 0))
        self.theme.currentIndexChanged.connect(self.set_theme)
        form.addRow(tr('Тема'), self.theme)
        from azimuth import updates
        from azimuth.settings import open_settings

        self.check_updates = QCheckBox(tr('Проверять обновления при запуске'))
        self.check_updates.setToolTip(tr('Раз при запуске программа спрашивает у GitHub номер последней версии (тот '
                                         'же выпуск, что на сайте) и предлагает скачать новую. Никаких ваших данных '
                                         'не отправляется.'))
        self.check_updates.setChecked(updates.enabled(open_settings()))
        self.check_updates.toggled.connect(lambda on: updates.set_enabled(open_settings(), on))
        form.addRow(self.check_updates)
        column.addWidget(box)

    def _files(self, column):
        box, form = self._box('files', 'Файлы')
        self.hydrogens = QCheckBox(tr('Достраивать водороды у файлов без H'))
        self.hydrogens.setToolTip(tr('Если в открытом файле нет ни одного атома H, они достраиваются по валентности '
                                     '(C 4, N 3, O 2…); файл с водородами не меняется'))
        on = self.studio.opening_tool.hydrogens_on_open() if hasattr(self.studio, 'opening_tool') else True
        self.hydrogens.setChecked(on)
        self.hydrogens.toggled.connect(self.set_hydrogens)
        form.addRow(self.hydrogens)
        column.addWidget(box)

    # -- bonds and steps, pictures, spectra (azimuth/defaults.py) ---------------------------------------------
    def _number(self, key, low, high, step, decimals, suffix=''):
        from azimuth import defaults

        field = QDoubleSpinBox()
        field.setRange(low, high)
        field.setSingleStep(step)
        field.setDecimals(decimals)
        field.setSuffix(suffix)
        field.setValue(defaults.get(key))
        field.valueChanged.connect(lambda value, k=key: self.put(k, value))
        return field

    def _switch(self, key, title, tip=''):
        from azimuth import defaults

        box = QCheckBox(tr(title))
        if tip:
            box.setToolTip(tr(tip))
        box.setChecked(defaults.get(key))
        box.toggled.connect(lambda on, k=key: self.put(k, on))
        return box

    def _reset_row(self, key, form):
        row = QHBoxLayout()
        row.addStretch(1)
        self.reset_buttons[key] = item = button(tr('По умолчанию'), lambda: self.reset(key))
        item.setToolTip(tr('Вернуть значения раздела, с которыми программа устанавливается'))
        row.addWidget(item)
        form.addRow(row)

    def _model(self, column):
        box, form = self._box('model', 'Связи и шаги')
        hint = label(tr('Связи по расстояниям — для структур без своих связей (XYZ, выводы расчётов); «Найти связи '
                        'заново» применяет множитель к открытой структуре.'), 'subtitle')
        hint.setWordWrap(True)
        form.addRow(hint)
        self.bond_factor = self._number('bond_factor', 1.05, 1.50, 0.01, 2, ' ×')
        self.bond_factor.setToolTip(tr('Связь, если расстояние не больше множителя × суммы ковалентных радиусов'))
        form.addRow(tr('Связь — до (× сумма ковалентных радиусов)'), self.bond_factor)
        self.bond_order = self._number('bond_order_min', 0.10, 1.00, 0.05, 2)
        self.bond_order.setToolTip(tr('«Связи по порядкам Майера»: связь, если порядок не меньше порога'))
        form.addRow(tr('Порог порядка связи'), self.bond_order)
        self.common_orientation = self._switch(
            'common_orientation', 'Шаги оптимизации и скана — в одной ориентации',
            'Каждый шаг поворачивается на начальную геометрию: молекула не прыгает (Gaussian в стандартной ориентации, '
            'сканы); длины и углы те же')
        form.addRow(self.common_orientation)
        self._reset_row('model', form)
        column.addWidget(box)

    def _pictures(self, column):
        from azimuth import defaults

        box, form = self._box('pictures', 'Снимки')
        self.picture_scale = QComboBox()
        for n in (2, 3, 4, 6):
            self.picture_scale.addItem(f'×{n}', n)
        self.picture_scale.setCurrentIndex(max(0, self.picture_scale.findData(defaults.get('picture_scale'))))
        self.picture_scale.setToolTip(tr('Во сколько раз больше экрана «Снимок высокого разрешения»'))
        self.picture_scale.currentIndexChanged.connect(
            lambda *_: self.put('picture_scale', self.picture_scale.currentData()))
        form.addRow(tr('Высокое разрешение'), self.picture_scale)
        self.picture_transparent = self._switch('picture_transparent', 'Прозрачный фон')
        form.addRow(self.picture_transparent)
        self.picture_crop = self._switch('picture_crop', 'Обрезать снимок по молекуле',
                                         'Выключено — сохраняется всё поле, как на экране')
        form.addRow(self.picture_crop)
        self._reset_row('pictures', form)
        column.addWidget(box)

    def _spectra(self, column):
        from azimuth import defaults

        box, form = self._box('spectra', 'Спектры')
        self.ir_style = QComboBox()
        self.ir_style.addItem(tr('Палочки'), 'sticks')
        self.ir_style.addItem(tr('Гауссова кривая'), 'gauss')
        self.ir_style.setCurrentIndex(max(0, self.ir_style.findData(defaults.get('ir_style'))))
        self.ir_style.currentIndexChanged.connect(lambda *_: self.put('ir_style', self.ir_style.currentData()))
        form.addRow(tr('ИК-спектр'), self.ir_style)
        self.ir_width = self._number('ir_width', 2, 200, 1, 0, tr(' см⁻¹'))
        self.ir_width.setToolTip(tr('Полная ширина полосы на половине высоты (FWHM)'))
        form.addRow(tr('Ширина полосы ИК'), self.ir_width)
        self.ir_scale_on = self._switch('ir_scale_on', 'Сразу включать множитель частот',
                                        'Если для метода и базиса результата множитель NIST CCCBDB известен')
        form.addRow(self.ir_scale_on)
        self.uv_fwhm = self._number('uv_fwhm', 0.05, 2.0, 0.05, 2, tr(' эВ'))
        self.uv_fwhm.setToolTip(tr('Полная ширина полосы на половине высоты (FWHM) — UV-Vis и ЭКД'))
        form.addRow(tr('Ширина полосы UV-Vis'), self.uv_fwhm)
        self._reset_row('spectra', form)
        column.addWidget(box)

    # -- the look of the model, units, programs, all the settings ----------------------------------------------
    def _choice(self, key, options):
        from azimuth import defaults

        field = QComboBox()
        for value, title in options:
            field.addItem(tr(title), value)
        field.setCurrentIndex(max(0, field.findData(defaults.get(key))))
        field.currentIndexChanged.connect(lambda *_, k=key, f=field: self.put(k, f.currentData()))
        return field

    def _view(self, column):
        from azimuth import defaults

        box, form = self._box('view', 'Вид модели')
        self.start_scheme = QComboBox()
        self.start_scheme.addItem(tr('Как в прошлый раз'), '')
        names = self.studio.scheme_tool.scheme_names() if hasattr(self.studio, 'scheme_tool') else []
        for name in names:
            self.start_scheme.addItem(tr(name), name)
        chosen = self.studio.scheme_tool.start_scheme() if hasattr(self.studio, 'scheme_tool') else ''
        self.start_scheme.setCurrentIndex(max(0, self.start_scheme.findData(chosen)))
        self.start_scheme.setToolTip(tr('Схема отображения, с которой открывается программа (меню «Вид → Схема '
                                        'отображения»); «Как в прошлый раз» — вид, оставленный при выходе'))
        self.start_scheme.currentIndexChanged.connect(self.set_start_scheme)
        form.addRow(tr('Схема при запуске'), self.start_scheme)
        self.quick_atoms = QSpinBox()
        self.quick_atoms.setRange(0, 5000)
        self.quick_atoms.setSingleStep(50)
        self.quick_atoms.setSpecialValueText(tr('никогда'))
        self.quick_atoms.setSuffix(tr(' атомов'))
        self.quick_atoms.setValue(defaults.get('quick_atoms'))
        self.quick_atoms.setToolTip(tr('Большая модель рисуется быстро и чуть грубее, и когда она стоит; '
                                       'снимки — всегда в полном качестве'))
        self.quick_atoms.valueChanged.connect(lambda value: self.put('quick_atoms', value))
        form.addRow(tr('Быстрая отрисовка — от'), self.quick_atoms)
        self._reset_row('view', form)
        column.addWidget(box)

    def set_start_scheme(self, *args):
        if hasattr(self.studio, 'scheme_tool'):
            return self.studio.scheme_tool.set_start_scheme(self.start_scheme.currentData() or '')
        return None

    def _units(self, column):
        box, form = self._box('units', 'Единицы')
        self.coordinate_unit = self._choice('coordinate_unit', COORDINATE_UNITS)
        self.coordinate_unit.setToolTip(tr('Таблица координат Компаса (форматы файлов — всегда в ангстремах)'))
        form.addRow(tr('Координаты'), self.coordinate_unit)
        self.energy_unit = self._choice('energy_unit', ENERGY_UNITS)
        self.energy_unit.setToolTip(tr('ΔE шагов оптимизации, сканов, IRC и конформеров; с этих единиц начинается '
                                       'диаграмма реакции'))
        form.addRow(tr('Энергии (ΔE)'), self.energy_unit)
        self._reset_row('units', form)
        column.addWidget(box)

    def _programs(self, column):
        from modules.sextant.inputs import KINDS, NAMES

        box, form = self._box('programs', 'Программы')
        hint = label(tr('Азимут сам ищет программы в PATH и обычных папках. Если программ несколько (две версии ORCA) '
                        'или нужная не найдена — укажите файл.'), 'subtitle')
        hint.setWordWrap(True)
        form.addRow(hint)
        self.program_paths, self.program_buttons = {}, {}
        for kind in KINDS:
            path = QLabel()
            path.setWordWrap(True)
            path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            choose = button(tr('Указать…'), lambda _=False, k=kind: self.choose_program(k))
            forget = button(tr('Искать самой'), lambda _=False, k=kind: self.forget_program(k))
            forget.setToolTip(tr('Забыть указанный файл и искать программу в PATH и обычных папках'))
            row = QHBoxLayout()
            row.addWidget(path, 1)
            row.addWidget(choose)
            row.addWidget(forget)
            form.addRow(NAMES[kind], row)
            self.program_paths[kind], self.program_buttons[kind] = path, (choose, forget)
            self._show_program(kind)
        column.addWidget(box)

    def _show_program(self, kind):
        from modules.sextant import runner

        configured = self.studio.run_tool.configured_program(kind) if hasattr(self.studio, 'run_tool') else None
        try:
            found = runner.find_program(kind, configured)
        except (OSError, ValueError):
            found = None
        if found is None:
            text = tr('не найдена')
        else:
            text = str(found) + ('' if configured and str(found) == str(configured) else tr(' · найдена сама'))
        self.program_paths[kind].setText(text)
        self.program_paths[kind].setToolTip(text)
        self.program_buttons[kind][1].setEnabled(bool(configured))
        return found

    def choose_program(self, kind, path=None):
        found = self.studio.run_tool.choose_program(kind, path) if hasattr(self.studio, 'run_tool') else None
        self._show_program(kind)
        return found

    def forget_program(self, kind):
        found = self.studio.run_tool.forget_program(kind) if hasattr(self.studio, 'run_tool') else None
        self._show_program(kind)
        return found

    def _all(self, column):
        box, form = self._box('all', 'Все настройки')
        hint = label(tr('Перенести настройки на другой компьютер или вернуть программу к виду после установки. Пароли '
                        'программа не хранит; ключи с pass, secret, token, private в файл не попадают.'), 'subtitle')
        hint.setWordWrap(True)
        form.addRow(hint)
        row = QHBoxLayout()
        self.export_button = button(tr('Сохранить в файл…'), lambda: self.export_settings())
        self.import_button = button(tr('Загрузить из файла…'), lambda: self.import_settings())
        self.reset_all_button = button(tr('Сбросить все настройки…'), lambda: self.reset_all())
        for item in (self.export_button, self.import_button, self.reset_all_button):
            row.addWidget(item)
        row.addStretch(1)
        form.addRow(row)
        self.all_note = label('', 'subtitle')
        self.all_note.setWordWrap(True)
        form.addRow(self.all_note)
        column.addWidget(box)

    def _store(self):
        return getattr(self.studio, 'preferences', None)

    def export_settings(self, path=None):
        """The settings as a JSON file (text, numbers, true/false, lists of text); None if cancelled."""
        import json
        from pathlib import Path

        from azimuth import crash_report

        store = self._store()
        if store is None:
            return None
        if path is None:
            from PySide6.QtWidgets import QFileDialog

            path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить настройки'), 'Azimuth-settings.json',
                                                  'JSON (*.json)')
            if not path:
                return None
        values = {}
        for key in sorted(store.allKeys()):
            value = store.value(key)
            if crash_report.SECRET.search(key):
                continue
            if isinstance(value, (str, int, float, bool)) or (isinstance(value, list)
                                                               and all(isinstance(v, str) for v in value)):
                values[key] = value
        Path(path).write_text(json.dumps({EXPORT_MARK: 1, 'values': values}, ensure_ascii=False, indent=1),
                              encoding='utf-8')
        self.all_note.setText(tr('Сохранено настроек: ') + str(len(values)) + ' · ' + str(path))
        return len(values)

    def import_settings(self, path=None):
        """The settings of a file of «Сохранить в файл…»; the number of values taken, None if cancelled or not such a
        file (the reason in all_note)."""
        import json
        from pathlib import Path

        from azimuth import crash_report

        store = self._store()
        if store is None:
            return None
        if path is None:
            from PySide6.QtWidgets import QFileDialog

            path, _ = QFileDialog.getOpenFileName(self, tr('Загрузить настройки'), '', 'JSON (*.json)')
            if not path:
                return None
        try:
            data = json.loads(Path(path).read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            self.all_note.setText(tr('Файл не прочитан: ') + str(exc))
            return None
        if not isinstance(data, dict) or data.get(EXPORT_MARK) != 1 or not isinstance(data.get('values'), dict):
            self.all_note.setText(tr('Это не файл настроек Азимута.'))
            return None
        taken = 0
        for key, value in data['values'].items():
            if isinstance(key, str) and key and not crash_report.SECRET.search(key):
                store.setValue(key, value)
                taken += 1
        store.sync()
        self._after_change()
        self.all_note.setText(tr('Загружено настроек: ') + str(taken)
                              + tr('. Часть из них (вид модели, папки) применится после перезапуска программы.'))
        return taken

    def reset_all(self, ask=True):
        """Every setting forgotten (the program as after its installation); False if the user said no."""
        store = self._store()
        if store is None:
            return False
        if ask:
            from PySide6.QtWidgets import QMessageBox

            from azimuth import quill

            answer = quill.question(self, tr('Сбросить все настройки'),
                                    tr('Забыть все настройки программы — вид, папки, пути к программам, сервер, '
                                       'свои схемы? Отменить это нельзя; можно сначала «Сохранить в файл…».'),
                                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                    QMessageBox.StandardButton.No, 'reset')
            if answer != QMessageBox.StandardButton.Yes:
                return False
        store.clear()
        store.sync()
        self._after_change()
        self.all_note.setText(tr('Все настройки сброшены. Вид модели и папки вернутся к исходным после перезапуска '
                                 'программы.'))
        return True

    def _after_change(self):
        """The values of azimuth/defaults read again, the open windows and this window follow them."""
        from azimuth import defaults

        defaults.load(self._store())
        for key in defaults.KEYS:
            if hasattr(self.studio, 'apply_default'):
                self.studio.apply_default(key)
        for section in RESET:
            self._show_values(section)
        for kind in getattr(self, 'program_paths', {}):
            self._show_program(kind)

    def put(self, key, value):
        """Keep a value of azimuth/defaults (in the settings of the program) and let the open windows follow."""
        from azimuth import defaults

        kept = defaults.put(key, value, getattr(self.studio, 'preferences', None))
        if hasattr(self.studio, 'apply_default'):
            self.studio.apply_default(key)
        return kept

    def reset(self, section):
        """«По умолчанию»: the values of the section as the program is installed."""
        from azimuth import defaults

        for key in RESET[section]:
            self.put(key, defaults.KEYS[key][1])
        if section == 'view':  # and the look of the last session at the start
            self.start_scheme.setCurrentIndex(0)
        self._show_values(section)
        return {key: defaults.get(key) for key in RESET[section]}

    def _show_values(self, section):
        """The fields of a section show the values of azimuth/defaults (without sending them again)."""
        from azimuth import defaults

        fields = {'bond_factor': self.bond_factor, 'bond_order_min': self.bond_order, 'ir_width': self.ir_width,
                  'uv_fwhm': self.uv_fwhm, 'quick_atoms': self.quick_atoms}
        switches = {'common_orientation': self.common_orientation, 'picture_transparent': self.picture_transparent,
                    'picture_crop': self.picture_crop, 'ir_scale_on': self.ir_scale_on}
        lists = {'picture_scale': self.picture_scale, 'ir_style': self.ir_style,
                 'coordinate_unit': self.coordinate_unit, 'energy_unit': self.energy_unit}
        for key in RESET[section]:
            value = defaults.get(key)
            widget = fields.get(key) or switches.get(key) or lists.get(key)
            widget.blockSignals(True)
            if key in fields:
                widget.setValue(value)
            elif key in switches:
                widget.setChecked(value)
            else:
                widget.setCurrentIndex(max(0, widget.findData(value)))
            widget.blockSignals(False)

    def _tables(self, column):
        from modules.spectrum.wavefunction import field_tables

        box, form = self._box('tables', 'Таблицы анализа (CSV)')
        hint = label(tr('Таблицы экстремумов, критических точек, спектров — в папке «Анализ» рядом с файлом расчёта. '
                        'Excel и Numbers с русской локалью открывают двойным щелчком «;» и десятичную запятую.'),
                     'subtitle')
        hint.setWordWrap(True)
        form.addRow(hint)
        separator, decimal = field_tables.style_parts(self.studio.surface_tool.csv_style() if hasattr(self.studio, 'surface_tool')
                                                      else field_tables.style)
        self.separator = QComboBox()
        for key, title in field_tables.SEPARATORS:
            self.separator.addItem(tr(title), key)
        self.separator.setCurrentIndex(max(0, self.separator.findData(separator)))
        self.decimal = QComboBox()
        for key, title in field_tables.DECIMALS:
            self.decimal.addItem(tr(title), key)
        self.decimal.setCurrentIndex(max(0, self.decimal.findData(decimal)))
        self.separator.currentIndexChanged.connect(self.set_table_style)
        self.decimal.currentIndexChanged.connect(self.set_table_style)
        form.addRow(tr('Разделитель столбцов'), self.separator)
        form.addRow(tr('Десятичный знак'), self.decimal)
        self.sample = QLabel()
        self.sample.setObjectName('settingsSample')
        form.addRow(tr('Так выглядит строка'), self.sample)
        self._show_sample()
        column.addWidget(box)

    def _jobs(self, column):
        box, form = self._box('jobs', 'Расчёты')
        self.jobs_folder = QLabel()
        self.jobs_folder.setWordWrap(True)
        self.jobs_folder.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.jobs_button = button(tr('Выбрать…'), self.choose_jobs_folder)
        row = QHBoxLayout()
        row.addWidget(self.jobs_folder, 1)
        row.addWidget(self.jobs_button)
        form.addRow(tr('Папка расчётов'), row)
        self._show_jobs_folder()
        # the root of the new projects («Документы/Azimuth/Проекты»)
        self.projects_folder = QLabel()
        self.projects_folder.setWordWrap(True)
        self.projects_folder.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.projects_button = button(tr('Выбрать…'), self.choose_projects_folder)
        row = QHBoxLayout()
        row.addWidget(self.projects_folder, 1)
        row.addWidget(self.projects_button)
        form.addRow(tr('Папка проектов'), row)
        self._show_projects_folder()
        # the best conformer of every structure of a queue before its calculation (batch_conformers.py)
        from modules.sextant.batch_conformers import METHODS

        self.conformer_switch = self._switch(
            'batch_conformers', 'Перед расчётом очереди искать лучший конформер каждой структуры',
            'Самый низкий конформер выбранным методом (газовая фаза, MMFF или GFN2-xTB) заменяет структуру, затем идёт '
            'расчёт очереди. Ион и комплексы очереди связывания не ищутся.')
        form.addRow(self.conformer_switch)
        self.conformer_method = self._choice('batch_conformer_method', [(key, title) for key, title, _ in METHODS])
        self.conformer_method.setToolTip('\n'.join(tr(title) + ' — ' + tr(note) for _, title, note in METHODS))
        self.conformer_method.setEnabled(self.conformer_switch.isChecked())
        self.conformer_switch.toggled.connect(self.conformer_method.setEnabled)
        form.addRow(tr('Метод поиска конформера'), self.conformer_method)
        column.addWidget(box)

    def _multiwfn(self, column):
        from modules.compass.actions.surface_actions import GRIDS

        box, form = self._box('multiwfn', 'Multiwfn')
        self.grid = QComboBox()
        for key, title in GRIDS:
            self.grid.addItem(tr(title), key)
        current = self.studio.surface_tool.nci_grid() if hasattr(self.studio, 'surface_tool') else 'low'
        self.grid.setCurrentIndex(max(0, self.grid.findData(current)))
        self.grid.currentIndexChanged.connect(self.set_grid)
        form.addRow(tr('Сетка расчёта'), self.grid)
        self.multiwfn_path = QLabel()
        self.multiwfn_path.setWordWrap(True)
        self.multiwfn_button = button(tr('Указать…'), self.choose_multiwfn)
        row = QHBoxLayout()
        row.addWidget(self.multiwfn_path, 1)
        row.addWidget(self.multiwfn_button)
        form.addRow(tr('Программа'), row)
        self._show_multiwfn()
        column.addWidget(box)

    def _errors(self, column):
        """Where the log of errors is, a report for the author, the folder of the logs."""
        from azimuth import crash_report

        box, form = self._box('errors', 'Ошибки')
        hint = label(tr('Ошибки программы записываются в журнал. Если что-то сломалось — отправьте автору отчёт (журналы, '
                        'версии программ, настройки без паролей).'), 'subtitle')
        hint.setWordWrap(True)
        form.addRow(hint)
        self.log_folder = QLabel(str(crash_report.log_dir()))
        self.log_folder.setWordWrap(True)
        self.log_folder.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        form.addRow(tr('Журналы'), self.log_folder)
        row = QHBoxLayout()
        self.send_button = button(tr('Отправить автору…'), self.send_report)
        self.send_button.setToolTip(tr('Отчёт на рабочий стол и письмо автору в почтовой программе: файл отчёта '
                                       'остаётся приложить к письму'))
        self.report_button = button(tr('Сохранить отчёт…'), self.save_report)
        self.logs_button = button(tr('Открыть папку журналов'), self.open_logs)
        row.addWidget(self.send_button)
        row.addWidget(self.report_button)
        row.addWidget(self.logs_button)
        row.addStretch(1)
        form.addRow(row)
        column.addWidget(box)

    def send_report(self):
        from azimuth import crash_report

        return crash_report.send_report(self, getattr(self.studio, 'preferences', None))

    def save_report(self):
        from azimuth import crash_report

        return crash_report.save_report_dialog(self, getattr(self.studio, 'preferences', None))

    def open_logs(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        from azimuth import crash_report

        folder = crash_report.log_dir()
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        return folder

    # -- what the choices do --------------------------------------------------------------------------------------------
    def show_section(self, key):
        box = self.boxes[key]
        for name, item in getattr(self, 'nav', {}).items():
            item.setProperty('active', name == key)
        self.scroll.ensureWidgetVisible(box, 0, 0)
        box.setFocus()
        return box

    def set_language(self, *args):
        code = self.language.currentData()
        if self.hub is not None and code and code != getattr(self.hub, 'language', None):
            self.hub.set_language(code)

    def set_theme(self, index):
        if hasattr(self.studio, 'set_theme_follows_system'):  # «Как в системе» — the third item
            if index == 2:
                self.studio.set_theme_follows_system(True)
                return
            self.studio.set_theme_follows_system(False)
        if (self.studio.theme.currentIndex() if hasattr(self.studio, 'theme') else index) == index:
            return
        if self.hub is not None and hasattr(self.hub, 'toggle_theme'):
            self.hub.toggle_theme()
        else:
            self.studio.theme.setCurrentIndex(index)

    def set_hydrogens(self, on):
        self.studio.preferences.setValue(self.studio.HYDROGENS_ON_OPEN, bool(on))
        action = getattr(self.studio, 'hydrogens_open_action', None)
        if action is not None and action.isChecked() != bool(on):
            action.blockSignals(True)
            action.setChecked(bool(on))
            action.blockSignals(False)

    def set_table_style(self, *args):
        from modules.spectrum.wavefunction import field_tables

        chosen = field_tables.style_code(self.separator.currentData(), self.decimal.currentData())
        if field_tables.style_parts(chosen)[1] != self.decimal.currentData():  # «,» between the columns: the point
            self.decimal.blockSignals(True)
            self.decimal.setCurrentIndex(self.decimal.findData(field_tables.style_parts(chosen)[1]))
            self.decimal.blockSignals(False)
        self.decimal.model().item(0).setEnabled(self.separator.currentData() != ',')
        if hasattr(self.studio, 'surface_tool'):
            self.studio.surface_tool.set_csv_style(chosen)
        else:
            field_tables.style = chosen
        self._show_sample()
        return chosen

    def _show_sample(self):
        from modules.spectrum.wavefunction import field_tables

        chosen = field_tables.style_code(self.separator.currentData(), self.decimal.currentData())
        separator, decimal = field_tables.style_parts(chosen)
        shown = '  ⇥  ' if separator == '\t' else separator
        self.sample.setText(shown.join(['C1', '-0' + decimal + '5000', '1' + decimal + '42']))
        self.decimal.model().item(0).setEnabled(separator != ',')

    def choose_jobs_folder(self, path=None):
        chosen = self.studio.run_tool.choose_jobs_folder(path) if hasattr(self.studio, 'run_tool') else None
        self._show_jobs_folder()
        return chosen

    def choose_projects_folder(self, path=None):
        chosen = self.studio.choose_projects_folder(path) if hasattr(self.studio, 'choose_projects_folder') else None
        self._show_projects_folder()
        return chosen

    def _show_projects_folder(self):
        folder = self.studio.projects_root() if hasattr(self.studio, 'projects_root') else ''
        self.projects_folder.setText(str(folder))
        self.projects_folder.setToolTip(str(folder))

    def _show_jobs_folder(self):
        folder = self.studio.run_tool.jobs_root() if hasattr(self.studio, 'run_tool') else ''
        self.jobs_folder.setText(str(folder))
        self.jobs_folder.setToolTip(str(folder))

    def set_grid(self, *args):
        if hasattr(self.studio, 'surface_tool'):
            self.studio.surface_tool.set_nci_grid(self.grid.currentData())

    def choose_multiwfn(self):
        chosen = self.studio.property_tool.choose_multiwfn_program() if hasattr(self.studio, 'property_tool') else None
        self._show_multiwfn()
        return chosen

    def _show_multiwfn(self):
        found = self.studio.property_tool.multiwfn_found() if hasattr(self.studio, 'property_tool') else None
        self.multiwfn_path.setText(str(found) if found is not None else tr('не найдена (brew install multiwfn или '
                                                                           'Multiwfn.exe)'))
