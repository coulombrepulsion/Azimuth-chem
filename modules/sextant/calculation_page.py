"""The building of the page of Sextant: the page itself, the card «Запуск расчёта», the further settings and the
box of the task. Methods of SextantWorkspace (self is the window), kept here to make workspace.py shorter.

Split off modules/sextant/workspace.py (0.222.29).
"""

import os
from PySide6.QtCore import QObject, Qt, QTimer
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QLabel,
    QLineEdit,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QFrame,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QToolButton,
    QVBoxLayout,
    QWidget,
)
from azimuth.core import DEFAULT_DISPERSION, DISPERSIONS, POPULATIONS, SCF_LEVELS, SOLVENTS, TDDFT_STATES, Calculation
from modules.sextant import inputs
from modules.sextant import remote
from modules.sextant.run_actions import PLACES
from modules.sextant.job_window import FamilyPicker, JobWindow, OptionsDialog
from azimuth import quill
from azimuth.ui import ElideLabel, button, card, icon_button, label
from azimuth.i18n import set_combo_key, tr
from modules.sextant.workspace_texts import DISPERSION_NAMES, ORCA_NOTICE, PROGRAMS
from modules.sextant.workspace_widgets import GuessPicker, WrappedNote


def calculation_page(self):
    page = QWidget()
    outer = QVBoxLayout(page)  # the tabs of Compass above, every tab has its own settings
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)  # the tabs right on the top edge of the cards, as in Compass (was 12 px of air)
    # the molecule page and the crystal card of Quantum ESPRESSO (crystal_mode.py) in one stack
    from PySide6.QtWidgets import QStackedWidget

    self.calc_stack = QStackedWidget()
    self.calc_body = QWidget()
    layout = QHBoxLayout(self.calc_body)
    layout.setContentsMargins(0, 0, 0, 0)
    layout.setSpacing(18)
    self.calc_stack.addWidget(self.calc_body)
    outer.addWidget(self.calc_stack, 1)
    column = QVBoxLayout()
    column.setContentsMargins(0, 0, 0, 0)  # level with the input file next to it
    column.setSpacing(18)
    frame, form_layout = card(tr('Постановка задачи'))
    form = QFormLayout()
    form.setSpacing(13)
    if os.name == 'nt':  # Segoe UI of Windows makes every row taller: the chain «Оптимизация + частоты → УФ-спектр →
        form.setVerticalSpacing(12)  # ЯМР» of ORCA needed 615 px of the 612 of a window of 1133 × 730 (2026-11-25)
    self.program = QComboBox()
    for key, name in PROGRAMS:
        # outside the beta: the name says so, the tip says why (inputs.UNVERIFIED)
        unchecked = key in inputs.UNVERIFIED
        self.program.addItem(f'{name} · {tr(inputs.UNVERIFIED_MARK)}' if unchecked else name, key)
        if unchecked:
            self.program.setItemData(self.program.count() - 1, tr(inputs.UNVERIFIED[key]),
                                     Qt.ItemDataRole.ToolTipRole)
    self.method = QComboBox(page)  # filled by apply_program with what the program knows
    self.basis = QComboBox(page)
    for combo in (self.method, self.basis):  # chosen through the families (FamilyPicker), kept as data
        combo.hide()
    self.method_picker = FamilyPicker(self.method)
    self.basis_picker = FamilyPicker(self.basis)
    self.task = QComboBox()
    self.fill_tasks('orca')  # refilled by apply_program with the tasks of the program
    set_combo_key(self.task, 'Оптимизация + частоты')
    self.charge = QSpinBox()
    self.charge.setRange(-20, 20)
    self.spin = QSpinBox()
    self.spin.setRange(1, 30)
    # charge and multiplicity — two short rows of the form, fields of one width under each other
    # (in one row with both captions they did not fit the column)
    for item in (self.charge, self.spin):
        item.setFixedWidth(84)
        item.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # the card of the molecule shows them
        item.valueChanged.connect(lambda *_: self.molecule_state_changed())
    self.charge.setToolTip(tr('Заряд · по умолчанию — по структуре молекулы'))
    self.spin.setToolTip(tr('Мультиплетность 2S + 1 · по умолчанию — по числу электронов'))
    self.state_note = label('', 'subtitle')  # «по структуре: 0 и 1» when changed by hand
    self.state_note.hide()
    self._state_formula = None
    self.cores = QSpinBox()
    self.cores.setRange(1, 128)
    self.cores.setValue(2)
    self.memory = QSpinBox()
    self.memory.setRange(100, 1000000)
    self.memory.setSingleStep(500)
    self.memory.setValue(1000)
    self.memory.setSuffix(tr(' МБ'))
    self.apply_machine(getattr(self, 'probe_machine', True))
    self.solvent = QComboBox()
    for key, row in SOLVENTS.items():
        self.solvent.addItem(tr(row[0]), key)
    self.dispersion = QComboBox()
    for key in DISPERSIONS:
        self.dispersion.addItem(tr(DISPERSION_NAMES[key]), key)
    self.dispersion.setCurrentIndex(self.dispersion.findData(DEFAULT_DISPERSION))
    self.build_advanced()
    # the name of the calculation — the first line of the file and the name of its files
    self.calc_title = QLineEdit()
    self.calc_title.setMaxLength(120)
    self.calc_title.setClearButtonEnabled(True)
    self.calc_title.setToolTip(tr('Первая строка входного файла и имя его файлов. Пусто — формула_метод_базис_растворитель.'))
    # the processes and the memory per process in the form (from the dialog), one row
    resources = QWidget()
    resources_row = QHBoxLayout(resources)
    resources_row.setContentsMargins(0, 0, 0, 0)
    resources_row.setSpacing(6)
    resources_row.addWidget(self.cores, 2)
    self.memory_times = QLabel('×')  # hidden with the memory (xtb, MOPAC)
    resources_row.addWidget(self.memory_times)
    resources_row.addWidget(self.memory, 3)
    self.cores.setSuffix(tr(' проц.'))
    for box in (self.cores, self.memory):  # they share the row and never push it over the card
        box.setMinimumWidth(80)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        box.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.solvent_widget = self.solvent_row()  # the row moves between the card and the dialog (setup_rows)
    self.resources_widget = resources
    main = [
        (tr('Название'), self.calc_title),
        (tr('Программа'), self.program),
        (tr('Задача'), self.task),
        (tr('Метод'), self.method_picker),
        (tr('Базис'), self.basis_picker),
        (tr('Растворитель'), self.solvent_widget),  # from «Дополнительные настройки…»; + model
        (tr('Дисперсия'), self.dispersion),
        (tr('Ресурсы'), resources),
    ]  # charge and multiplicity moved into «Дополнительные настройки…» (they follow the structure)
    extra = [  # the dialog «Дополнительные настройки…»; more for advanced users
        (tr('Электронное состояние'), None),  # the first group, open — from the main form
        (tr('Заряд'), self.charge),
        (tr('Мультиплетность'), self.spin),
        ('', self.state_note),
        (tr('SCF и интегрирование'), None),
        (tr('Сходимость SCF'), self.scf_level),
        (tr('Трудная сходимость'), self.slow_conv),
        (tr('Сетка DFT'), self.grid),
        ('', self.no_ri),
        ('', self.rijcosx),
        ('', self.auto_aux),
        (tr('Релятивистские поправки'), None),
        (tr('Гамильтониан'), self.relativistic),
        ('', self.relativistic_note),
        (tr('Базисы по элементам'), None),
        (tr('Базисы'), self.element_basis_row),
        ('', self.element_basis_note),
        # «Оптимизация и частоты» and «Возбуждённые состояния (TD-DFT)» moved to the form, under the task
        (tr('Свойства и вывод'), None),
        (tr('Заряды на атомах'), self.population),
        ('', self.orbitals),
        # the start from the orbitals
        # of an earlier calculation of ORCA (MORead) — was a row under the task in the form
        (tr('Начальное приближение'), None),
        (tr('Орбитали'), self.guess),
        # the fields taken out of «Постановка задачи» (modules/sextant/setup_rows.py); «Поля…» chooses them
        (tr('Задача'), None),
        ('', self.task_form_note()),
    ]  # no field of one's own keywords — the input file itself can be edited
    for title, widget in main:
        form.addRow(title, widget)
    # the steps of a chain chosen in «Задача», under it (chain_steps.ChainSteps)
    from modules.sextant.chain_steps import ChainSteps

    self.chain_steps = ChainSteps(self)
    form.insertRow(form.getWidgetPosition(self.task)[0] + 1, self.chain_steps)
    form.setRowVisible(self.chain_steps, False)
    self.main_form = form  # rows a program does not use are hidden (apply_program)
    self.options_dialog = OptionsDialog(  # all the groups folded — the dialog as tall as their headings
        page, extra, tr('Ограничения оптимизации и путь реакции задаются в Компасе («Правка»).'), opened=0
    )
    row = QHBoxLayout()
    # sliders — the gear is the server profile
    self.options_button = icon_button(tr('Дополнительные настройки…'), self.show_options, 'sliders')
    self.options_button.setToolTip(tr('Заряд и мультиплетность, SCF и RIJCOSX, релятивистские поправки, свойства'))
    row.addWidget(self.options_button)
    # «Поля…» — which fields stand in the card, the rest are in the section «Задача» of the dialog
    self.fields_button = icon_button(tr('Поля…'), self.show_setup_fields, 'setup-fields')
    self.fields_button.setToolTip(tr('Какие поля показывать в «Постановке задачи»; остальные — в «Дополнительных '
                                     'настройках…», раздел «Задача»'))
    row.addWidget(self.fields_button)
    self.options_summary = ElideLabel('', 'subtitle')
    row.addWidget(self.options_summary, 1)
    self.options_row = row  # at the foot of the card, under the settings of the task
    self.program.currentIndexChanged.connect(self.program_changed)
    self.program.activated.connect(self.run_tool.program_chosen)  # chosen by the user
    self.task.activated.connect(self.task_chosen)  # a task chosen by the user brings its method
    for widget in (self.task, self.method, self.basis, self.solvent, self.dispersion, self.scf_level, self.grid,
                   self.opt_conv, self.population, self.relativistic, self.slow_conv, self.tddft_mode,
                   self.solvent_model):
        widget.currentTextChanged.connect(self.settings_changed)
    for widget in (self.charge, self.spin, self.cores, self.memory, self.max_cycles, self.states, self.temperature,
                   self.pressure, self.root, self.scan_end, self.scan_steps, self.cda_charge, self.cda_mult1,
                   self.cda_mult2, self.scan2_end, self.scan2_steps):
        widget.valueChanged.connect(self.settings_changed)
    self.cda_atoms.textChanged.connect(self.settings_changed)
    self.element_basis.textChanged.connect(self.settings_changed)
    for widget in (self.cda_charge, self.cda_mult1, self.cda_mult2):  # the note under the task tells the fragments
        widget.valueChanged.connect(lambda *_: self.update_task_box())
    self.cda_atoms.textChanged.connect(lambda *_: self.update_task_box())
    self.scan_index.activated.connect(self.scan_coordinate_chosen)
    self.scan2_index.activated.connect(self.scan2_coordinate_chosen)
    for widget in (self.no_ri, self.ts, self.calc_hessian, self.orbitals, self.rijcosx, self.auto_aux, self.num_freq,
                   self.stability, self.nto,
                   self.triplets, self.raman, self.couplings):
        widget.toggled.connect(self.settings_changed)
    self.calc_title.textChanged.connect(self.settings_changed)
    self.build_task_box()  # the settings of the chosen task, rows of the form under the main ones
    self.build_setup_rows()  # what stands in the card and what in the dialog (the owner's choice)
    form_layout.addLayout(form)
    # the advised method and basis set are in the tooltips and the first item of the pickers
    self.advice = None
    self.update_options_summary()
    form_layout.addStretch()
    form_layout.addLayout(self.options_row)
    # the rough time of the calculation in the place freed by the compact «Запуск расчёта»; the electrons,
    # multiplicity and memory moved to the card of the molecule (right, above the input file)
    self.time_estimate = label('', 'notice')  # one line in its box (WrappedNote made the box twice as tall)
    self.time_estimate.setWordWrap(True)
    self.time_estimate.setToolTip(
        tr('Очень приблизительно: по числу базисных функций, методу, задаче и числу процессов, для обычного ноутбука; на кластере быстрее.')
    )
    # the time is shown in the card of the molecule, next to what is calculated
    # the lines of the molecule ask for the height of their text: at 1133 × 730 the card gave them less, and the
    # first and last lines were cut (0.222.0)
    self.state_info = WrappedNote()
    self.state_info.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)  # under the formula, no gap
    # the card never scrolls: it is as tall as its fields, the rarer ones are in the dialog (setup_rows)
    from PySide6.QtWidgets import QFrame as _Frame, QScrollArea

    class FitScroll(QScrollArea):
        """The column is as wide as the card needs, plus its scroll bar — the card is never squeezed
        under its fields (the scroll area of 0.216.142 took the width of the bar from the card)."""

        def _width(self, hint):
            """As wide and as tall as the card needs: the card never scrolls (the owner, 0.222.0 — the fields
            set less often are in «Дополнительные настройки…», setup_rows)."""
            inner = self.widget()
            if inner is not None:
                need = inner.minimumSizeHint()
                hint.setWidth(need.width() + 2 * self.frameWidth())
                hint.setHeight(need.height() + 2 * self.frameWidth())
            return hint

        def minimumSizeHint(self):
            return self._width(super().minimumSizeHint())

        def cap_combos(self):
            """A list of the card is as wide as the column gives it, never as its longest item: «Цепочка:
            Оптимизация + частоты → энергия в большем базисе» made the task 460 px and the card 648 — wider than the
            column (500), whose edge cut the fields. The open list still shows every item whole (wide_popup)."""
            inner = self.widget()
            for combo in inner.findChildren(QComboBox) if inner is not None else ():
                if combo.sizeAdjustPolicy() != QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon:
                    combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
                    combo.setMinimumContentsLength(12)

        def eventFilter(self, watched, event):
            from PySide6.QtCore import QEvent

            if watched is self.widget() and event.type() == QEvent.Type.LayoutRequest:
                self.cap_combos()  # the rows of another task may bring lists of their own
                self.fit_column()
                self.updateGeometry()  # the rows of another task: another width
            return super().eventFilter(watched, event)

        preferred = 0  # the width wished for the column (set below); the fields may need more

        def fit_column(self):
            """The column keeps its preferred width unless the fields need more: then as wide as they need. A
            fixed maximum under the minimum of the card cut its fields on the right (a row of two fields, as
            «Сходимость» with its cycles, is 386 px beside the labels: 574 in all)."""
            column = self.parentWidget()
            if column is not None and self.preferred:
                column.setMaximumWidth(max(self.preferred, self.minimumSizeHint().width()))

    self.setup_scroll = FitScroll()
    self.setup_scroll.setObjectName('setupScroll')
    self.setup_scroll.setWidgetResizable(True)
    self.setup_scroll.setFrameShape(_Frame.Shape.NoFrame)
    self.setup_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    self.setup_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)  # no scrolling
    # the scroll area and its viewport see through; the card itself keeps its white — «> QWidget > QWidget»
    # (the child of the viewport) was the card, and it showed the grey of the window (0.222.4)
    self.setup_scroll.setStyleSheet('QScrollArea#setupScroll, QScrollArea#setupScroll > QWidget#qt_scrollarea_viewport '
                                    '{background: transparent;}')
    self.setup_scroll.setWidget(frame)
    self.setup_scroll.cap_combos()
    column.addWidget(self.setup_scroll, 1)  # «Запуск расчёта» joined the card of the molecule on the right
    setup = QWidget()  # a narrower column for the setup, the input file gets the rest
    setup.setLayout(column)
    # wider only when the fields need it (fit_column)
    self.setup_scroll.preferred = 500
    self.setup_scroll.fit_column()
    layout.addWidget(setup, 2)
    right = QVBoxLayout()  # the molecule to be calculated above the input file
    right.setContentsMargins(0, 0, 0, 0)
    right.setSpacing(18)
    layout.addLayout(right, 3)
    from modules.sextant.molecule_card import MoleculeThumb

    # one card — the molecule, a thin grey rule, the launch (were «Что считаем» and «Запуск расчёта»); no
    # title, the arrow to Compass in the corner
    self.calc_card, calc_layout = card('')
    calc_title = calc_layout.itemAt(0).widget()
    calc_layout.removeWidget(calc_title)
    calc_title.deleteLater()
    self.to_compass_button = icon_button(tr('К молекуле в Компасе'), lambda: self.navigate(0), 'back')
    calc_row = QHBoxLayout()
    calc_row.setSpacing(16)
    self.calc_thumb = MoleculeThumb()
    self.calc_thumb.setFixedSize(160, 118)  # lower: the input file below gets the room (0.222.7; was 190 × 150)
    self.calc_thumb.setToolTip(tr('Структура вкладки · потяните мышью, чтобы повернуть'))
    calc_row.addWidget(self.calc_thumb)
    # no atoms yet — Quill instead of the empty model; her own pose, the sextant at her eye looking
    # to the right, towards «К молекуле в Компасе» (was the magnifier of Spectrum), clear edges cut off
    self.calc_quill = QLabel()
    self.calc_quill.setProperty('quill', True)
    self.calc_quill.setAlignment(Qt.AlignmentFlag.AlignCenter)
    self.calc_quill.setFixedSize(160, 118)  # the place of the thumbnail of the model
    picture = quill.trimmed_pixmap('sextant-empty', 114)
    if not picture.isNull():
        self.calc_quill.setPixmap(picture)
    self.calc_quill.hide()
    calc_row.addWidget(self.calc_quill)
    info = QVBoxLayout()
    # Windows: the lines of Segoe UI made this column 136 px, taller than the picture (118), and the card took the
    # room of the input file below (2026-11-25); macOS: the picture is the taller, the gaps change nothing there
    info.setSpacing(3 if os.name == 'nt' else 6)
    self.calc_formula = QLabel()
    self.calc_formula.setObjectName('calcFormula')
    info.addWidget(self.calc_formula)
    info.addWidget(self.state_info)
    info.addStretch(1)
    info.addWidget(self.time_estimate)  # from under the settings — the card had empty room
    calc_row.addLayout(info, 1)
    calc_row.addWidget(self.to_compass_button, 0, Qt.AlignmentFlag.AlignTop)
    calc_layout.addLayout(calc_row)
    self.batch_banner = self.batch_tool.build_batch_banner()  # the queue chosen — seen in the card of the
    # calculation
    calc_layout.addWidget(self.batch_banner)
    self.calc_rule = QFrame()
    self.calc_rule.setObjectName('panelRule')
    self.calc_rule.setFixedHeight(1)
    calc_layout.addWidget(self.calc_rule)
    self.run_card(calc_layout)
    self.run_frame = self.calc_card
    right.addWidget(self.calc_card)

    class FitHeight(QObject):
        """The card of the molecule is as tall as its rows need at its width, no more: its size hint counts the
        wrapped lines (the state of the molecule, the estimate of the time) as if the card were narrow, and on a
        large window the layout gave it that height — empty room under the method and the task, which the input
        file below could use (the owner, 2026-11-22)."""

        def eventFilter(self, watched, event):
            from PySide6.QtCore import QEvent

            if event.type() in (QEvent.Type.Resize, QEvent.Type.LayoutRequest, QEvent.Type.Show):
                need = watched.layout().heightForWidth(watched.width())
                need = max(need, watched.minimumSizeHint().height()) if need > 0 else 0
                if need and need != watched.maximumHeight():
                    watched.setMaximumHeight(need)
            return False

    self._calc_card_fit = FitHeight(self.calc_card)
    self.calc_card.installEventFilter(self._calc_card_fit)
    preview, preview_layout = card(tr('Входной файл ORCA'))
    self.preview_card = preview  # the calculation takes its place while it is shown
    self.preview_title = preview_layout.itemAt(0).widget()
    # the title of the input in a row («К молекуле в Компасе» moved to the card of the molecule)
    preview_layout.removeWidget(self.preview_title)
    title_row = QHBoxLayout()
    title_row.setSpacing(8)
    # the title and «?» on one line (centred on each other); one line of text, not wrapped
    self.preview_title.setWordWrap(False)
    self.preview_title.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
    title_row.addWidget(self.preview_title, 0, Qt.AlignmentFlag.AlignVCenter)
    # what the lines of the file mean — behind «?», not under the file
    self.input_help_button = QToolButton()
    self.input_help_button.setObjectName('helpButton')
    self.input_help_button.setText('?')
    self.input_help_button.setFixedSize(22, 22)
    self.input_help_button.setCursor(Qt.CursorShape.PointingHandCursor)
    self.input_help_button.setAccessibleName(tr('Как устроен входной файл'))
    self.input_help_button.clicked.connect(self.show_input_help)
    title_row.addWidget(self.input_help_button, 0, Qt.AlignmentFlag.AlignVCenter)
    title_row.addStretch(1)
    # open an input file of ORCA or Gaussian — its molecule, its settings, the file itself to run
    self.open_input_button = icon_button(tr('Открыть входной файл…'), lambda: self.input_tool.open_input_file(), 'file-open')
    title_row.addWidget(self.open_input_button, 0, Qt.AlignmentFlag.AlignVCenter)
    # the same settings for every structure of the set of the tab (Compass, «Структуры»)
    self.set_inputs_button = icon_button(tr('Входные файлы для всего набора структур…'), lambda: self.input_tool.export_set_inputs(),
                                         'save')
    self.set_inputs_button.hide()
    title_row.addWidget(self.set_inputs_button, 0, Qt.AlignmentFlag.AlignVCenter)
    # the same settings for the conformers or the structures of the drawer, run one after another
    self.batch_button = icon_button(tr('Очередь расчётов для набора…'), lambda: self.batch_tool.open_batch_dialog(), 'queue')
    self.batch_button.setCheckable(True)  # pressed (blue) while a queue is chosen
    self.batch_button.hide()
    title_row.addWidget(self.batch_button, 0, Qt.AlignmentFlag.AlignVCenter)
    self.resume_batch_button = icon_button(tr('Продолжить очередь'), lambda: self.batch_tool.resume_batch(), 'forward')
    self.resume_batch_button.hide()
    title_row.addWidget(self.resume_batch_button, 0, Qt.AlignmentFlag.AlignVCenter)
    self.saved_batches_button = button(tr('Пакеты…'), lambda: self.batch_tool.show_saved_batches())
    self.saved_batches_button.setToolTip(tr('Открыть сохранённый пакет расчётов целиком'))
    title_row.addWidget(self.saved_batches_button, 0, Qt.AlignmentFlag.AlignVCenter)
    # the input file can take the whole column (the card of the molecule folds away)
    self.expand_input_button = icon_button(tr('Развернуть'), self.toggle_input_expanded, 'expand')
    self.expand_input_button.setCheckable(True)
    title_row.addWidget(self.expand_input_button, 0, Qt.AlignmentFlag.AlignVCenter)
    preview_layout.insertLayout(0, title_row)
    # the editor of the program (azimuth/text_editor.py) — the line numbers, find and replace, go to a line, the
    # lines duplicated, moved, commented…, the status line; Ctrl+S saves the file, Ctrl+O opens one
    from azimuth.text_editor import CodeEdit, EditorPane

    self.preview = CodeEdit()
    self.preview.setFont(QFont('Menlo', 12))
    # Ctrl+S saves the file as it is in the editor, of the program chosen (export_program_input; the edit kept)
    self.preview_pane = EditorPane(self.preview, save=lambda: self.input_tool.export_program_input(),
                                   open_=lambda: self.input_tool.open_input_file())
    # the file can be edited; the edit stays until «Собрать заново», another program or another tab
    self.input_edited = False
    self._edit_base = ''
    self._filling_preview = False
    self.preview.textChanged.connect(self.input_tool.input_text_changed)
    preview_layout.addWidget(self.preview_pane, 1)
    edited = QHBoxLayout()
    edited.setSpacing(8)
    self.input_edited_note = label('', 'subtitle')
    self.input_edited_note.setWordWrap(True)
    self.reset_input_button = icon_button(tr('Собрать файл заново по настройкам'), self.input_tool.reset_input, 'undo')
    edited.addWidget(self.input_edited_note, 1)
    edited.addWidget(self.reset_input_button)
    self.input_edited_row = QWidget()
    self.input_edited_row.setLayout(edited)
    edited.setContentsMargins(0, 0, 0, 0)
    self.input_edited_row.hide()
    preview_layout.addWidget(self.input_edited_row)
    self.input_error = label('', 'error')
    self.input_error.hide()
    preview_layout.addWidget(self.input_error)
    self.preview_notice = label(tr(ORCA_NOTICE), 'notice')  # the text of «?»; no longer under the file
    self.preview_notice.hide()
    self.input_help_button.setToolTip(tr(ORCA_NOTICE))
    self.export_button = icon_button(tr('Сохранить входной файл .inp'), self.input_tool.export_input, 'save')
    self.export_button.hide()
    bottom = QHBoxLayout()
    bottom.setSpacing(8)
    note = label(
        tr(
            'Файл можно править прямо здесь — перед запуском он проверяется. Расчёт запускается в своей папке внутри папки расчётов (какая это папка, показывает кнопка с папкой); результат откроется в Компасе или в Спектре.'
        ),
        'subtitle',
    )
    note.setWordWrap(True)
    bottom.addWidget(note, 1)
    # «Окно расчёта» at the bottom right — where the calculation has «Входной файл», the arrow the other way
    bottom.addWidget(self.job_window_button, 0, Qt.AlignmentFlag.AlignBottom)
    preview_layout.addLayout(bottom)
    right.addWidget(preview, 1)
    right.addWidget(self.job_slot, 1)  # shown instead of the input file while the calculation is
    self.calc_stack.addWidget(self.crystal_mode_tool.build())
    self.stack.addWidget(page)
    # Ctrl+Enter starts the calculation, Ctrl+. stops it
    # (⌘↩ and ⌘. on a Mac), anywhere on the page of Sextant, the editor of the input included
    from PySide6.QtGui import QKeySequence, QShortcut

    self.run_shortcuts = []
    for keys, slot in (('Ctrl+Return', self.run_by_key), ('Ctrl+Enter', self.run_by_key),
                       ('Ctrl+.', self.stop_by_key)):
        shortcut = QShortcut(QKeySequence(keys), page)
        shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        shortcut.activated.connect(slot)
        self.run_shortcuts.append(shortcut)
    saved = self.preferences.value('sextant_program', 'orca')
    self.program.blockSignals(True)  # the molecule and the tables are not built yet
    self.program.setCurrentIndex(max(0, self.program.findData(saved)))
    self.program.blockSignals(False)
    self.apply_program()
    self.run_tool.refresh_program_path()


def run_card(self, box):
    """The launch under the molecule (in the card of the molecule, below a thin rule)."""
    # where the calculation runs — this computer or a server (two switches with icons)
    row = QHBoxLayout()
    row.setSpacing(0)
    self.where_group = QButtonGroup(self)
    self.where_group.setExclusive(True)
    self.where_buttons = {}
    from azimuth.ui import SegmentButton

    row.setSpacing(6)
    for key, title, glyph, tip in (
        ('local', tr('Этот компьютер'), 'computer', tr('Считать на этом компьютере')),
        ('server', tr('Сервер'), 'server', tr('Считать на сервере (кластере) — профиль: «Сервер…»')),
    ):
        item = SegmentButton(title, glyph, tip)  # the chosen one unfolds its name smoothly
        item.clicked.connect(lambda checked=False, key=key: self.run_tool.set_where(key))
        self.where_group.addButton(item)
        self.where_buttons[key] = item
        row.addWidget(item)
    # one row — where to calculate, the program and its tick (was two rows)
    where_row = row
    self.where = 'server' if self.preferences.value(remote.WHERE_KEY, 'local') == 'server' else 'local'
    self.where_buttons[self.where].setChecked(True)
    self.run_tool.fold_where()
    self.job_timer = QTimer(self)
    self.job_timer.setInterval(1000)
    self.job_timer.timeout.connect(self.run_tool.poll_job)
    row = where_row
    row.addSpacing(10)
    # the mark of the program, its name and a tick when it is found; the path only in the tooltip
    self.program_badge = QLabel()
    self.program_badge.setFixedSize(22, 22)
    row.addWidget(self.program_badge)
    self.program_path = ElideLabel('', 'subtitle')
    row.addWidget(self.program_path, 1)
    self.program_found = QLabel('✓')
    self.program_found.setStyleSheet('color: #2e9e5b; font-weight: 700; font-size: 15px;')
    self.program_found.hide()
    row.addWidget(self.program_found)
    self.choose_program_button = icon_button(tr('Указать…'), self.run_tool.choose_program, 'file-open')
    row.addWidget(self.choose_program_button)
    self.server_button = icon_button(tr('Сервер…'), self.run_tool.edit_server, 'gear')  # the profile
    self.server_button.hide()
    row.addWidget(self.server_button)
    # the files of the server and of this computer side by side (server_browser.py)
    self.server_files_button = icon_button(tr('Файлы на сервере'), self.run_tool.open_server_files, 'server-files')
    self.server_files_button.hide()
    row.addWidget(self.server_files_button)
    # does the server answer now — a tick or a cross next to the button
    self.check_server_button = icon_button(tr('Проверить подключение к серверу'), self.run_tool.check_server, 'ping')
    self.check_server_button.hide()
    row.addWidget(self.check_server_button)
    from azimuth.controls import Spinner

    self.server_spinner = Spinner(16)  # while it logs in — no window, only this
    row.addWidget(self.server_spinner)
    self.server_mark = QLabel()
    self.server_mark.hide()
    row.addWidget(self.server_mark)
    box.addLayout(row)
    # the program is not found — Quill with a torch next to what to do
    self.program_missing = QWidget()
    missing = QHBoxLayout(self.program_missing)
    missing.setContentsMargins(0, 0, 0, 0)
    missing.setSpacing(10)
    self.program_missing_picture = QLabel()
    self.program_missing_picture.setProperty('quill', True)  # hides the hub's scales
    picture = quill.pixmap('program-missing', 72)
    if not picture.isNull():
        self.program_missing_picture.setPixmap(picture)
    missing.addWidget(self.program_missing_picture, 0, Qt.AlignmentFlag.AlignTop)
    self.program_missing_text = label('', 'subtitle')
    missing.addWidget(self.program_missing_text, 1)
    # xtb, CREST and MOPAC come from conda-forge — installed into the folder of the program at one click
    self.install_missing_button = icon_button(tr('Установить в папку программы…'),
                                              lambda: self.run_tool.install_tools_dialog((self.program_kind(),)), 'download')
    self.install_missing_button.hide()
    missing.addWidget(self.install_missing_button, 0, Qt.AlignmentFlag.AlignTop)
    self.program_missing.hide()
    box.addWidget(self.program_missing)
    # the note on the calculation programs is gone (it is in the manual and next to a program not found)
    row = QHBoxLayout()
    row.setSpacing(8)
    self.run_button = button(tr('Запустить расчёт'), self.run_tool.run_calculation, True)
    # the progress, the log, «Остановить» and «Папка расчёта» live in the window of the calculation
    for place in PLACES:  # a window for the calculation of each place
        with self.at_place(place):
            self.job_window = JobWindow(self)
            self.job_window.place = place
            self.job = None
    self.output_window = None
    self.run_time = label('', 'subtitle')  # only the time next to the button; the rest in the tooltip
    self.run_time.hide()
    self.job_window_button = icon_button(tr('Окно расчёта'), self.show_job_window, 'forward')
    self.job_window_button.hide()
    # 0.249.5: no «Папка для расчётов…» here (the owner: «не запускается, ее можно убрать и оставить Папка расчета») —
    # where the calculations go is chosen in «Настройки → Расчёты»; «Папка расчёта» of the calculation shown stands in
    # job_controls_slot with «Остановить» and «Вывод программы» (JobWindow.place_controls)
    self.job_controls_slot = QWidget()
    controls = QHBoxLayout(self.job_controls_slot)
    controls.setContentsMargins(0, 0, 0, 0)
    controls.setSpacing(8)
    self.job_controls_slot.hide()  # until a calculation's card is docked
    if os.name == 'nt':  # Open MPI is not for Windows; ORCA needs Microsoft MPI
        # installed at one click from conda-forge (msmpi: mpiexec.exe, smpd.exe), as Open MPI elsewhere
        self.mpi_button = icon_button(tr('Установить MS-MPI…'), lambda: self.run_tool.install_tools_dialog(('openmpi',)),
                                      'download')
    else:
        self.mpi_button = icon_button(tr('Установить Open MPI…'), lambda: self.run_tool.install_tools_dialog(('openmpi',)), 'download')
    self.mpi_button.hide()
    self.install_job = None
    self.install_timer = QTimer(self)
    self.install_timer.setInterval(500)
    self.install_timer.timeout.connect(self.run_tool.poll_install)
    row.addWidget(self.run_button)
    from azimuth.controls import Spinner

    self.run_spinner = Spinner(18)  # logging in to the server before a calculation — no waiting window
    row.addWidget(self.run_spinner)
    row.addWidget(self.run_time)
    row.addWidget(self.job_controls_slot)
    row.addStretch()
    row.addWidget(self.mpi_button)
    box.addLayout(row)
    # the calculation as a card in the place of the input file (added to the right column below)
    self.job_slot = QWidget()
    slot = QVBoxLayout(self.job_slot)
    slot.setContentsMargins(0, 0, 0, 0)
    slot.setSpacing(0)
    self.job_slot.hide()
    # _job_shown, job_panel_open (False after «Входной файл»: the file is shown) — of each place, see _PerPlace
    self.stack.currentChanged.connect(lambda *_: self.job_follow())
    return box


# advanced settings, charge and multiplicity from the molecule, resources, the advice ------------
def build_advanced(self):
    self.scf_level = QComboBox()
    for key, name in SCF_LEVELS.items():
        self.scf_level.addItem(tr(name), key)
    self.scf_level.setCurrentIndex(self.scf_level.findData('tight'))
    self.grid = QComboBox()
    self.grid.addItem(tr('Как в программе'), '')
    self.grid.addItem(tr('Мельче (точнее, дольше)'), 'fine')
    self.no_ri = QCheckBox(tr('Без RI-приближения (точнее, дольше)'))
    # ORCA only — RIJCOSX (the default of ORCA for hybrid DFT; here asked for explicitly, e.g. for HF)
    self.rijcosx = QCheckBox(tr('RIJCOSX — быстрее кулоновский и обменный вклады (ORCA)'))
    self.rijcosx.setToolTip(tr('ORCA: RI для кулоновского вклада и COSX для обменного; для базиса не из def2 добавляется def2/J. С «Без RI» не совместимо.'))
    self.no_ri.toggled.connect(lambda off: self.rijcosx.setEnabled(not off and self.program_kind() == 'orca'))
    self.ts = QCheckBox(tr('Искать переходное состояние (седло)'))
    self.ts.setToolTip(tr('ORCA OptTS, Gaussian Opt=(TS,CalcFC), Psi4 opt_type TS; гессиан считается в начале. Начинайте '
                          'со структуры, близкой к седлу: вершины скана, середины пути NEB. Из минимума (вода, '
                          'любая устойчивая молекула) поиск идёт сотни циклов и не сходится.'))
    self.opt_conv = QComboBox()
    self.opt_conv.addItem(tr('Обычная'), 'normal')
    self.opt_conv.addItem(tr('Строгая (Tight)'), 'tight')
    self.max_cycles = QSpinBox()
    self.max_cycles.setRange(0, 2000)
    self.max_cycles.setSpecialValueText(tr('как в программе'))
    self.max_cycles.setValue(Calculation().max_cycles)  # 100, 0 — the program's own
    self.calc_hessian = QCheckBox(tr('Точный гессиан в начале оптимизации'))
    self.population = QComboBox()
    for key, name in POPULATIONS.items():
        self.population.addItem(tr(name), key)
    self.orbitals = QCheckBox(tr('Записать орбитали в вывод (для Спектра)'))
    self.states = QSpinBox()
    self.states.setRange(1, 100)
    self.states.setValue(TDDFT_STATES)
    self.temperature = QDoubleSpinBox()
    self.temperature.setRange(1.0, 5000.0)
    self.temperature.setDecimals(2)
    self.temperature.setValue(298.15)
    self.temperature.setSuffix(' K')
    self.pressure = QDoubleSpinBox()
    self.pressure.setRange(0.001, 1000.0)
    self.pressure.setDecimals(3)
    self.pressure.setValue(1.0)
    self.pressure.setSuffix(tr(' атм'))
    self._extra = ''
    self._isotopes = ''  # Calculation.isotopes («Изотопы выделенных атомов…» of Compass)
    # relativity, a hard SCF, AutoAux, numerical frequencies, TD-DFT
    from azimuth.core import RELATIVISTIC, SLOW_CONV, TDDFT_MODES

    self.relativistic = QComboBox()
    for key, name in RELATIVISTIC.items():
        self.relativistic.addItem(tr(name), key)
    self.relativistic.setToolTip(tr('Скалярный релятивистский гамильтониан — для атомов от 4-го периода (Rb и тяжелее он '
                                    'нужен). Базис берите перестроенный под него: DKH-def2-…, ZORA-def2-…, x2c-… (ORCA).'))
    self.relativistic_note = label(tr('ORCA: DKH, ZORA, X2C; Gaussian: DKH2; Psi4 и xtb — без поправок.'), 'subtitle')
    self.relativistic_note.setWordWrap(True)
    self.slow_conv = QComboBox()
    for key, name in SLOW_CONV.items():
        self.slow_conv.addItem(tr(name), key)
    self.slow_conv.setToolTip(tr('Если SCF не сходится (переходные металлы, радикалы): ORCA SlowConv / VerySlowConv '
                                 '(демпфирование), Gaussian SCF=XQC, Psi4 damping_percentage.'))
    self.auto_aux = QCheckBox(tr('AutoAux — вспомогательные базисы из орбитального (ORCA)'))
    self.auto_aux.setToolTip(tr('ORCA строит вспомогательные базисы RI сам — для базиса, у которого нет своего /J или /C.'))
    self.num_freq = QCheckBox(tr('Численные частоты (если нет аналитических)'))
    self.num_freq.setToolTip(tr('ORCA NumFreq, Gaussian Freq=Numer, Psi4 по энергиям: медленнее, но для любых методов.'))
    # the solvation model next to the solvent, the stability analysis under «Энергия»
    self.solvent_model = QComboBox()
    self.solvent_model.addItem('CPCM', 'cpcm')
    self.solvent_model.addItem('SMD', 'smd')
    self.solvent_model.setToolTip(tr('CPCM — электростатика растворителя; SMD добавляет неэлектростатические вклады — '
                                     'для энергий сольватации, pKa (ORCA, Gaussian)'))
    self.stability = QCheckBox(tr('Проверить устойчивость волновой функции'))
    self.stability.setToolTip(tr('Ищет решение SCF ниже найденного (радикалы, бирадикалы, металлы) и переходит к '
                                 'нему: ORCA %scf STABPerform, Gaussian Stable=Opt'))
    self.raman = QCheckBox(tr('Спектр комбинационного рассеяния (Раман, ORCA)'))
    self.raman.setToolTip(tr('Активности Рамана вместе с частотами: ORCA считает их только численно (NumFreq) — '
                             'расчёт частот станет в несколько раз дольше.'))
    self.couplings = QCheckBox(tr('Константы спин-спинового взаимодействия (КССВ, ORCA)'))
    self.couplings.setToolTip(tr('Все J между ядрами H, C, F, P — мультиплеты в спектре ЯМР Спектра; расчёт дольше '
                                 'экранирования в несколько раз (лучше базис pcJ-1)'))
    self.tddft_mode = QComboBox()
    for key, name in TDDFT_MODES.items():
        self.tddft_mode.addItem(tr(name), key)
    self.tddft_mode.setToolTip(tr('TDA — приближение Тамма — Данкова (ORCA по умолчанию), полное TD-DFT — RPA '
                                  '(Gaussian по умолчанию).'))
    self.triplets = QCheckBox(tr('Триплетные состояния тоже'))
    self.nto = QCheckBox(tr('Натуральные переходные орбитали (NTO)'))
    self.nto.setToolTip(tr('Каждое возбуждение — одна-две пары орбиталей «откуда → куда» вместо длинного списка; '
                           'в Спектре — на модели Компаса (ORCA DoNTO)'))
    self.root = QSpinBox()
    self.root.setRange(1, 100)
    self.root.setValue(1)
    self.root.setToolTip(tr('Для задачи «Оптимизация возбуждённого состояния (TD-DFT)»: какое состояние (1 — первое '
                            'возбуждённое)'))
    # the relaxed scan — a bond, angle or dihedral among the constraints of Compass, its end, the points
    self.scan_index = QComboBox()
    self.scan_index.setToolTip(tr('Что сканировать — длина, угол или двугранный угол из ограничений оптимизации '
                                  'Компаса; начало — значение в нынешней геометрии'))
    self.scan_end = QDoubleSpinBox()
    self.scan_end.setRange(-360.0, 360.0)
    self.scan_end.setDecimals(3)
    self.scan_end.setPrefix(tr('до '))
    self.scan_end.setToolTip(tr('Конечное значение координаты: Å для длины, градусы для углов'))
    self.scan_steps = QSpinBox()
    self.scan_steps.setRange(2, 100)
    self.scan_steps.setValue(10)
    self.scan_steps.setSuffix(tr(' точек'))
    self.scan_steps.setToolTip(tr('Число точек скана вместе с началом и концом; в каждой — оптимизация остального'))
    self._scan_shown = ()  # the coordinates listed in scan_index: [(kind, atoms)]
    # the second coordinate of a two-dimensional scan (ORCA) — «Нет» or one of the same list
    self.scan2_index = QComboBox()
    self.scan2_index.setToolTip(tr('Двумерный скан (ORCA): для каждой точки первой координаты — все точки второй; '
                                   'карта энергии — в Компасе (☰ → «Карта скана»)'))
    self.scan2_end = QDoubleSpinBox()
    self.scan2_end.setRange(-360.0, 360.0)
    self.scan2_end.setDecimals(3)
    self.scan2_end.setPrefix(tr('до '))
    self.scan2_end.setToolTip(tr('Конечное значение второй координаты'))
    self.scan2_steps = QSpinBox()
    self.scan2_steps.setRange(2, 40)
    self.scan2_steps.setValue(5)
    self.scan2_steps.setSuffix(tr(' точек'))
    self.scan2_steps.setToolTip(tr('Число точек второй координаты; всего точек — произведение двух чисел'))
    self.guess = GuessPicker(self)  # MORead
    self.guess.changed.connect(self.settings_changed)
    # CDA — fragment 1 (the donor) by its atoms, its charge and multiplicity; fragment 2 — the rest
    self.cda_atoms = QLineEdit()
    self.cda_atoms.setPlaceholderText(tr('атомы: N1, H2–H4 или 1-4'))
    self.cda_atoms.setToolTip(tr('Атомы фрагмента 1 — донора (например, лиганда); фрагмент 2 — остальные атомы '
                                 '(акцептор, например металл с другими лигандами). Номера — как в Компасе.'))
    self.cda_pick = QPushButton(tr('Из выделения'))
    self.cda_pick.setToolTip(tr('Атомы, выделенные в Компасе, — фрагмент 1'))
    self.cda_pick.clicked.connect(lambda: self.cda_from_selection())
    self.cda_charge = QSpinBox()
    self.cda_charge.setRange(-10, 10)
    self.cda_charge.setPrefix(tr('заряд '))
    self.cda_charge.setToolTip(tr('Заряд фрагмента 1; у фрагмента 2 — заряд комплекса минус этот'))
    self.cda_mult1 = QSpinBox()
    self.cda_mult1.setRange(1, 11)
    self.cda_mult1.setPrefix('2S+1 = ')
    self.cda_mult1.setToolTip(tr('Мультиплетность фрагмента 1'))
    self.cda_mult2 = QSpinBox()
    self.cda_mult2.setRange(1, 11)
    self.cda_mult2.setPrefix('2S+1 = ')
    self.cda_mult2.setToolTip(tr('Мультиплетность фрагмента 2'))
    # own basis sets of some elements (Calculation.element_basis)
    self.element_basis = QLineEdit()
    self.element_basis.setPlaceholderText('Fe=def2-TZVP; Cl=def2-SVP')
    self.element_basis.setToolTip(tr('Элемент=базис через «;». ORCA — блок %basis NewGTO, Gaussian — Gen, Psi4 — '
                                     'basis { assign }; элементы, которых здесь нет, берут базис расчёта.'))
    self.element_basis_add = QPushButton(tr('Добавить…'))
    self.element_basis_add.setToolTip(tr('Выбрать элемент молекулы и его базис'))
    self.element_basis_add.clicked.connect(lambda: self.add_element_basis())
    self.element_basis_row = QWidget()
    pair = QHBoxLayout(self.element_basis_row)
    pair.setContentsMargins(0, 0, 0, 0)
    pair.addWidget(self.element_basis, 1)
    pair.addWidget(self.element_basis_add)
    self.element_basis_note = label(tr('Свой базис для отдельных элементов — например, def2-TZVP на металле и '
                                       'def2-SVP на остальных атомах.'), 'subtitle')
    self.element_basis_note.setWordWrap(True)


def build_task_box(self):
    """«Настройки задачи» — the settings of the chosen task and program (inputs.task_options) as rows of the
    form itself (one column of captions with the rows above; were the sections «Оптимизация и частоты» and
    «Возбуждённые состояния» of «Дополнительные настройки…»): only the rows the program writes into its input;
    the heading is hidden when there are none."""
    form = self.main_form
    box = QWidget()  # a thin rule and the heading, one row spanning the form
    column = QVBoxLayout(box)
    column.setContentsMargins(0, 6, 0, 0)
    column.setSpacing(10)
    rule = QFrame()
    rule.setObjectName('panelRule')
    rule.setFixedHeight(1)
    column.addWidget(rule)
    self.task_heading = label('', 'eyebrow')
    column.addWidget(self.task_heading)
    form.addRow(box)
    self.task_box = box
    self.max_cycles.setToolTip(tr('Предел циклов оптимизации'))
    self.max_cycles.setSuffix(tr(' циклов'))
    self.root.setPrefix(tr('корень '))  # next to the number of states: which one is optimized
    self.states.setToolTip(tr('Сколько возбуждённых состояний считать'))
    for field in (self.max_cycles, self.temperature, self.pressure, self.states, self.root, self.scan_end,
                  self.scan_steps, self.cda_charge, self.cda_mult1, self.cda_mult2, self.scan2_end, self.scan2_steps):
        field.setAlignment(Qt.AlignmentFlag.AlignCenter)  # as the fields of the form above
    self.task_rows = []
    for caption, keys in self.TASK_ROWS:
        if len(keys) == 1:
            widget = getattr(self, keys[0])
        else:
            widget = QWidget()
            pair = QHBoxLayout(widget)
            pair.setContentsMargins(0, 0, 0, 0)
            pair.setSpacing(6)
            for key in keys:
                pair.addWidget(getattr(self, key), 1)
        if caption:
            form.addRow(tr(caption), widget)
        else:
            form.addRow(widget)
        self.task_rows.append((widget, keys, caption))
    self.task_note = WrappedNote()  # NEB: where its settings are; all its lines (the form gave it one)
    form.addRow(self.task_note)
    self.task.currentIndexChanged.connect(lambda *_: self.update_task_box())
    self.task.currentIndexChanged.connect(lambda *_: self.show_chain_steps())
    for combo in (self.method, self.basis):  # the steps not chosen by hand follow the form
        combo.currentIndexChanged.connect(lambda *_: self.chain_steps.sync() if hasattr(self, 'chain_steps') else None)
    self.update_task_box()
    self.show_chain_steps()
