"""Sextant for a crystal: the page of the calculation of a crystal tab, as that of a molecule.

§1 PURPOSE
    Sextant for a crystal looks as for a molecule; its programs are those of crystals only (and those of molecules
    are not offered for a crystal). A crystal tab of Compass has in Sextant the cards a
    molecule has: «Постановка задачи» on the left (the name, the program — Quantum ESPRESSO only —, the task and the
    settings of pw.x, qe_window.QePanel.rows), the card of the crystal on the right (its model, formula, group, cell,
    the atoms computed, the run), the input file under it (edited by hand like that of ORCA).
§2 ALGORITHM
    One QePanel (compact=False) holds the settings and the run; build() lays its controls out in the cards. The page
    is a second widget of calc_stack of the window. navigate(1) from «Компас · Кристалл» keeps the crystal tabs
    (Compass stays in its crystal mode) and calls follow(the tab): its crystal goes into the panel, the crystal page is
    shown; from «Компас · Молекула» follow(None) shows the page of the molecule. set_compass_mode while Sextant is shown
    (a project tab of another kind chosen there) calls follow too.
§4 SPECIFICATION
    CrystalModeTool(window): build() -> QWidget; active; panel; program_combo; follow(document) -> bool;
    enter(document=None) -> bool; leave(); update_card().
§7 TESTS
    tests/gui/test_gui_files.py::test_sextant_quantum_espresso.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (QFormLayout, QHBoxLayout, QLabel, QLineEdit, QVBoxLayout,
                               QWidget)

from azimuth.i18n import tr

QE_KEY = 'qe'
QE_NAME = 'Quantum ESPRESSO'


STAGES = (  # (key, mark in the output, text) — the stages of a run of pw.x shown as passed
    ('scf', 'convergence has been achieved', 'Самосогласованное поле сошлось'),
    ('relax', 'bfgs converged', 'Оптимизация сошлась'),
    ('bands', 'End of band structure calculation', 'Зоны вдоль пути посчитаны'),
    ('dos', 'Program DOS', 'Плотность состояний считается'),
    ('done', 'JOB DONE.', 'pw.x закончил работу'),
)


CP2K_STAGES = (  # the stages of a run of CP2K
    ('scf', 'SCF run converged', 'Самосогласованное поле сошлось'),
    ('opt', 'OPTIMIZATION STEP:', 'Начата оптимизация геометрии'),
    ('opt-done', 'GEOMETRY OPTIMIZATION COMPLETED', 'Оптимизация сошлась'),
    ('molden', 'SCF run converged', 'Волновая функция записана (.molden)'),  # and its file is there
    ('done', 'PROGRAM ENDED AT', 'CP2K закончил работу'),
)


def make_job_card(window, panel):
    """The card of a running calculation of Sextant (job_window.JobWindow — Quill counting, the bar, the stages) for the
    job of the panel: its buttons rewired to the panel (stop, the output, the folder, back to the input file)."""
    from PySide6.QtCore import QUrl
    from PySide6.QtGui import QDesktopServices

    from modules.sextant.job_window import JobWindow, OutputWindow

    card = JobWindow(window)
    for item, action in ((card.stop_button, panel.stop), (card.output_button, lambda: open_output(card, panel)),
                         (card.folder_button, lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(str(panel.folder)))
                          if panel.folder is not None else None),
                         # as after the run of a molecule — the results of the crystal in Compass («Атомы», «Связи») and
                         # Spectrum
                         (card.compass_button, lambda: window.navigate(0)),
                         (card.spectrum_button, lambda: window.navigate(2))):
        item.clicked.disconnect()
        item.clicked.connect(lambda *_, a=action: a())
    for item in (card.skip_button, card.qtaim_button, card.compass_button, card.spectrum_button):
        item.hide()

    def open_output(card, panel):
        if panel.folder is None:
            return None
        if getattr(card, 'output_window', None) is None:
            card.output_window = OutputWindow(window)
        return card.output_window.watch((panel.folder / 'pw.out',))

    return card


CRYSTALS_UNVERIFIED = ('Запуск Quantum ESPRESSO и CP2K проверен (на этом компьютере и на сервере), но числа ещё не '
                       'сверены с литературой на известных кристаллах — сверяйте результаты сами.')


class CrystalModeTool:
    PORT = (
        'calc_body',
        'calc_stack',
        'crystal',
        'crystal_tool',
        'document',
        'main_form',
        'navigate',
        'notify',
        'own_molecule',
        'program',
        'project_kind',
        'run_tool',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)
        self.active = False
        self.panel = None
        self.page = None

    # -- the page ------------------------------------------------------------------------------------------------
    def build(self):
        from azimuth.ui import card, icon_button, label
        from modules.compass.actions.qe_window import QePanel
        from modules.sextant.molecule_card import MoleculeThumb

        page = QWidget()
        outer = QHBoxLayout(page)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(18)
        panel = self.panel = QePanel(self.w.widget, None, '', page, compact=False, where_in_form=False)
        panel.where_in_form = False  # where to compute — the switches by «Запустить расчёт», as for a molecule
        panel.hide()  # the holder of the controls and of the run; they live in the cards
        # «Постановка задачи»
        frame, layout = card(tr('Постановка задачи') + ' · ' + tr('не проверено'))
        # outside the beta (AGENTS.md §0): the crystals are shown, marked — in the title, with the reason in its tip (a
        # line of its own pushed the fields of the card over the window of a laptop)
        self.unverified = layout.itemAt(0).widget()
        self.unverified.setToolTip(tr(CRYSTALS_UNVERIFIED))
        form = QFormLayout()
        form.setSpacing(13)
        self.calc_title = QLineEdit()
        self.calc_title.setMaxLength(120)
        self.calc_title.setClearButtonEnabled(True)
        self.calc_title.setToolTip(tr('Имя папки расчёта. Пусто — имя кристалла и задача.'))
        form.addRow(tr('Название'), self.calc_title)
        self.program_combo = panel.program_box  # Quantum ESPRESSO or CP2K — the first row of the panel the rows of the
        # molecule page — Название, Программа, Задача, Метод, Базис, Дисперсия, Ресурсы, then the rows of the task (the
        # grid of k, the cell, the supercell, the thresholds); the electronic state and the SCF go into «Дополнительные
        # настройки…» at the foot of the card, as the charge, the multiplicity and the SCF of a molecule
        main, extra = self.crystal_rows(panel)
        for title, widget in main:
            form.addRow(title, widget)
        panel.form = form
        from modules.sextant.job_window import OptionsDialog

        from modules.sextant import setup_rows as sr

        # the fields taken out of «Постановка задачи», as on the page of a molecule (setup_rows); «Поля…» chooses them
        moved_note = label(sr.task_form_note(), 'subtitle')
        moved_note.setWordWrap(True)
        extra = extra + [(tr('Задача'), None), ('', moved_note)]
        self.options_dialog = OptionsDialog(page, extra, tr('Ячейка с зарядом нейтрализуется однородным фоном: энергии '
                                                            'заряженных ячеек разного размера напрямую не сравнивают.'))
        panel.extra_forms = self.options_dialog.forms
        keys = ('program', 'task', 'method', 'method', 'basis', 'cut', 'cut', 'density', 'vdw', 'vdw', 'resources', 'k',
                'k', 'primitive', 'supercell', 'relax')  # the rows of crystal_rows, in their order
        if len(keys) != len(main):
            raise RuntimeError('the keys of the rows of a crystal do not match crystal_rows')
        rows = [('calc_title', self.calc_title)] + [(key, widget) for key, (_, widget) in zip(keys, main)]
        self.setup_rows = sr.SetupRows(None, form, self.options_dialog.forms[-1], rows, key=sr.CRYSTAL_KEY,
                                       movable=sr.CRYSTAL_MOVABLE, defaults=sr.CRYSTAL_DEFAULT_OUTSIDE,
                                       titles=sr.CRYSTAL_TITLES, store=getattr(self.w.widget, 'preferences', None),
                                       after=panel.show_rows)  # the rows of the other program hidden again
        panel.update_where()
        panel.show_rows()
        self.align_with_molecule()
        # «Постановка задачи» of a molecule: the form right in the card — its margins none (the form in a widget of its
        # own got the margins of the style: the rows stood further right and lower than those of a molecule) and the
        # background that of the card
        form.setContentsMargins(0, 0, 0, 0)
        holder = QWidget()
        holder.setObjectName('crystalForm')
        holder.setStyleSheet('QWidget#crystalForm {background: transparent;}')
        # the form inside a column, as on the page of a molecule: a widget whose own layout is a form gets colons after
        # the names of its rows (polish.colon_labels) — «Программа:» here, «Программа» there
        holder_column = QVBoxLayout(holder)
        holder_column.setContentsMargins(0, 0, 0, 0)
        holder_column.addLayout(form)
        holder_column.addStretch(1)
        # the values in the middle of their fields, as the processes and the memory of a molecule (were at the left)
        from PySide6.QtWidgets import QAbstractSpinBox

        for _, widget in rows:
            for spin in [widget] + widget.findChildren(QAbstractSpinBox):
                if isinstance(spin, QAbstractSpinBox):
                    spin.setAlignment(Qt.AlignmentFlag.AlignCenter)
        # no scrolling (0.222.0, as the page of a molecule): the rarer fields are in «Дополнительные настройки…»
        layout.addWidget(holder, 1)
        layout.addWidget(panel.note)
        from azimuth.ui import ElideLabel

        options_row = QHBoxLayout()
        self.options_button = icon_button(tr('Дополнительные настройки…'), self.show_options, 'sliders')
        self.options_button.setToolTip(tr('Заряд ячейки, спин, DFT+U, заполнение и сходимость SCF'))
        options_row.addWidget(self.options_button)
        self.fields_button = icon_button(tr('Поля…'), self.show_setup_fields, 'setup-fields')
        self.fields_button.setToolTip(tr('Какие поля показывать в «Постановке задачи»; остальные — в «Дополнительных '
                                         'настройках…», раздел «Задача»'))
        options_row.addWidget(self.fields_button)
        self.options_summary = ElideLabel('', 'subtitle')
        options_row.addWidget(self.options_summary, 1)
        layout.addLayout(options_row)
        for box in (panel.occupations, panel.conv, panel.eps_scf, panel.program_box, panel.order):
            box.currentIndexChanged.connect(lambda *_: self.update_options_summary())
        panel.charge.valueChanged.connect(lambda *_: self.update_options_summary())
        panel.spin.toggled.connect(lambda *_: self.update_options_summary())
        panel.hubbard.textChanged.connect(lambda *_: self.update_options_summary())
        self.update_options_summary()
        setup = QWidget()
        column = QVBoxLayout(setup)
        column.setContentsMargins(0, 0, 0, 0)
        column.addWidget(frame, 1)
        setup.setMaximumWidth(500)
        outer.addWidget(setup, 2)
        right = QVBoxLayout()
        right.setContentsMargins(0, 0, 0, 0)
        right.setSpacing(18)
        outer.addLayout(right, 3)
        # the card of the crystal and the run
        crystal_card, crystal_layout = card('')
        title = crystal_layout.itemAt(0).widget()
        crystal_layout.removeWidget(title)
        title.deleteLater()
        row = QHBoxLayout()
        row.setSpacing(16)
        self.thumb = MoleculeThumb()
        self.thumb.setFixedSize(190, 150)
        self.thumb.setToolTip(tr('Кристалл вкладки · потяните мышью, чтобы повернуть'))
        row.addWidget(self.thumb)
        info = QVBoxLayout()
        info.setSpacing(6)
        self.formula = QLabel()
        self.formula.setObjectName('calcFormula')
        info.addWidget(self.formula)
        self.facts = label('', 'subtitle')
        self.facts.setWordWrap(True)
        info.addWidget(self.facts)
        info.addStretch(1)
        row.addLayout(info, 1)
        back = icon_button(tr('К кристаллу в Компасе'), lambda: self.w.navigate(0), 'back')
        row.addWidget(back, 0, Qt.AlignmentFlag.AlignTop)
        crystal_layout.addLayout(row)
        rule = QWidget()
        rule.setObjectName('panelRule')
        rule.setFixedHeight(1)
        crystal_layout.addWidget(rule)
        # this computer or the server — the two switches of the page of a molecule, then the state
        from PySide6.QtWidgets import QButtonGroup

        from azimuth.ui import SegmentButton

        place = QHBoxLayout()
        place.setSpacing(6)
        self.where_group = QButtonGroup(page)
        self.where_group.setExclusive(True)
        self.where_buttons = {}
        for key, text, glyph, tip in (('local', tr('Этот компьютер'), 'computer', tr('Считать на этом компьютере')),
                                      ('server', tr('Сервер'), 'server', tr('Считать на сервере (кластере) — профиль: «Сервер…»'))):
            item = SegmentButton(text, glyph, tip)
            item.clicked.connect(lambda checked=False, key=key: self.set_where(key))
            self.where_group.addButton(item)
            self.where_buttons[key] = item
            place.addWidget(item)
        self.where_buttons['local'].setChecked(True)
        # with the server chosen — its profile and its files, as on the page of a molecule (the owner's Windows,
        # 2026-11-24: in «Компас · Кристалл» there were neither)
        self.server_button = icon_button(tr('Сервер…'), self.edit_server, 'gear')
        self.server_files_button = icon_button(tr('Файлы на сервере'), lambda: self.w.run_tool.open_server_files(),
                                               'server-files')
        for item in (self.server_button, self.server_files_button):
            item.hide()
            place.addWidget(item)
        place.addSpacing(10)
        place.addWidget(panel.status, 1)
        crystal_layout.addLayout(place)
        # the buttons of the page of a molecule: «Запустить расчёт» blue, the others with their words.
        # The buttons of Multiwfn
        # are not on this page — the charges and the AIM bonds of a run are in Compass («Атомы», «Связи»,
        # 0.147.0) and in Spectrum, reached by «Перейти в Компас» / «Перейти в Спектр» of the finished calculation, as
        # for a molecule; those of the panel stay inside it, hidden with it
        from azimuth.ui import button

        for name, text, call, primary in (('run_button', 'Запустить расчёт', panel.run_clicked, True),  # or the batch
                                          ('stop_button', 'Остановить', panel.stop, False),
                                          ('open_button', 'Открыть оптимизированную ячейку', panel.open_relaxed, False),
                                          ('plot_button', 'Показать график', panel.show_plot, False)):
            old = getattr(panel, name)
            new = button(tr(text), call, primary)
            new.setEnabled(old.isEnabled())
            # the plot — after a calculation of the bands or of the DOS
            new.setVisible(name != 'plot_button')
            setattr(panel, name, new)
            old.deleteLater()
        # after a CP2K run the five buttons in one row were wider than
        # the card and pressed the column of the settings narrow — now they go on to a second row
        from azimuth.ui import flow_layout

        buttons = flow_layout(8)
        for b in (panel.run_button, panel.stop_button, panel.open_button, panel.plot_button):
            buttons.addWidget(b)
        crystal_layout.addLayout(buttons)
        crystal_layout.addWidget(panel.summary)
        right.addWidget(crystal_card)
        # the input file
        preview_card, preview_layout = card(tr('Входной файл Quantum ESPRESSO'))
        self.preview_title = preview_layout.itemAt(0).widget()
        panel.program_listener = lambda kind: self.preview_title.setText(
            tr('Входной файл CP2K') if kind == 'cp2k' else tr('Входной файл Quantum ESPRESSO'))
        head = preview_layout.itemAt(0).widget()
        preview_layout.removeWidget(head)
        head.setWordWrap(False)
        top = QHBoxLayout()
        top.addWidget(head)
        top.addStretch(1)
        top.addWidget(panel.reset_button)
        preview_layout.insertLayout(0, top)
        preview_layout.addWidget(getattr(panel, 'preview_pane', panel.preview), 1)  # with its find bar
        preview_layout.addWidget(panel.edited_note)
        # no name of the folder (it is «Расчёты» only on macOS and Linux and can be chosen; in English and
        # Chinese the Russian name stood in the text) — the button with the folder shows it
        note = label(tr('Файл можно править прямо здесь. Расчёт запускается в своей папке — в папке проекта или в папке '
                        'расчётов (какая это папка, показывает кнопка с папкой); зоны и плотность состояний — кнопкой '
                        'после расчёта.'), 'subtitle')
        note.setWordWrap(True)
        preview_layout.addWidget(note)
        right.addWidget(preview_card, 1)
        self.preview_card = preview_card
        # the calculation in the place of the input file while it runs (and after it, until «Входной файл»)
        self.job_slot = QWidget()
        slot = QVBoxLayout(self.job_slot)
        slot.setContentsMargins(0, 0, 0, 0)
        self.job_card = make_job_card(self.w.widget, panel)
        self.job_card.dock(self.job_slot)
        self.job_card.input_button.clicked.disconnect()
        self.job_card.input_button.clicked.connect(lambda *_: self.show_input())
        self.job_slot.hide()
        right.addWidget(self.job_slot, 1)
        # the installation of the programs (the window of a calculation of the molecule page) in the same place, as on
        # the page of a molecule — it went into the hidden card of the molecule and nothing was seen (0.222.5)
        self.install_slot = QWidget()
        install = QVBoxLayout(self.install_slot)
        install.setContentsMargins(0, 0, 0, 0)
        self.install_slot.hide()
        right.addWidget(self.install_slot, 1)
        panel.listeners.append(self.job_event)
        self.calc_title.textChanged.connect(lambda text: setattr(panel, 'title_text', text.strip()))
        panel.task.currentIndexChanged.connect(lambda _: self.update_card())
        for box in panel.supercell:
            box.valueChanged.connect(lambda _: self.update_card())
        panel.primitive.toggled.connect(lambda _: self.update_card())
        self.page = page
        return page

    def update_card(self):
        """The model of the tab, its formula and what is computed: the group, the cell, the atoms of the cell computed."""
        from modules.compass.chemistry import crystal as cr

        panel = self.panel
        data = panel.crystal
        if data is None or self.page is None:
            return
        try:
            molecule = self.w.own_molecule()
        except Exception:  # noqa: BLE001 — the model of the tab is only a picture here
            molecule = None
        # while a job runs the panel keeps its crystal — the picture is that of the tab only when the
        # tab holds the crystal computed; else the picture of the crystal computed stays, and a line says why
        tab = getattr(self.w, 'crystal', None)
        other = not tab or tab[0] is not data
        if molecule is not None and not other:
            self.thumb.set_molecule(molecule)
            viewer = self.w.viewer
            self.thumb.set_palette(getattr(viewer, 'palette', {}))
            self.thumb.set_dark(getattr(viewer, 'dark', False))
        computed, _ = panel.computed()
        c = data.cell
        # the formula of the crystal (its cell), not of the block of atoms on the screen («ClCs₈» for CsCl)
        from modules.compass.chemistry import crystal_symmetry

        formula = ((data.formula_sum or '').replace(' ', '') or crystal_symmetry.empirical_formula(data)
                   or (molecule.formula if molecule is not None else data.title))
        self.formula.setText(formula.translate(str.maketrans('0123456789', '₀₁₂₃₄₅₆₇₈₉')))
        stem = panel.name.rsplit('.', 1)[0] if panel.name.lower().endswith('.cif') else panel.name
        self.calc_title.setPlaceholderText(f'{stem}_{panel.task.currentData()}'.replace(' ', '_'))
        lines = [data.space_group or 'P 1',
                 tr('Ячейка файла: a = {}, b = {}, c = {} Å; α = {}, β = {}, γ = {}°').format(
                     *(f'{v:.3f}' for v in (c.a, c.b, c.c)), *(f'{v:.2f}' for v in (c.alpha, c.beta, c.gamma))),
                 tr('Считается: {} атомов в ячейке').format(len(cr.unit_cell(computed)))]
        if other and panel.job is not None and panel.job.running:
            lines.append(tr('Идёт расчёт этого кристалла — кристалл открытой вкладки можно поставить после него.'))
        self.facts.setText('\n'.join(lines))

    # -- entering and leaving --------------------------------------------------------------------------------------
    def enter(self, document=None):
        if self.page is None:
            return False
        built = getattr(self.w, 'crystal', None)
        if not built:
            self.w.notify(tr('Quantum ESPRESSO и CP2K считают кристаллы: откройте файл CIF в «Компас · Кристалл».'), 10000)
            return False
        data = built[0]
        name = getattr(self.w.crystal_tool, 'crystal_name', '') or data.title or 'CIF'
        own = getattr(self.w.document(), 'research_project_path', '')  # the name of its project
        if own:
            from azimuth import crystal_projects

            if crystal_projects.is_crystal(own):
                name = crystal_projects.title(own)
        self.panel.update_where()  # a server set up since
        self.panel.apply_machine()  # the processes and the memory of this computer (unless changed here)
        self.sync_where()
        if self.panel.crystal is not data and not self.panel.set_crystal(data, name):
            self.w.notify(tr('Идёт расчёт — другой кристалл можно выбрать после него.'), 6000)
        self.update_card()
        self.align_with_molecule()  # the fonts and the language of now
        self.w.calc_stack.setCurrentWidget(self.page)
        self.active = True
        return True

    def show_input(self):
        self.job_slot.hide()
        if hasattr(self, 'install_slot'):
            self.install_slot.hide()
        self.preview_card.show()

    def show_install(self, job_window):
        """The window of the installation in the place of the input file of the crystal."""
        job_window.dock(self.install_slot)
        self.preview_card.hide()
        self.job_slot.hide()
        self.install_slot.show()
        return job_window

    def shows_install(self, job_window):
        return job_window.docked and job_window.parentWidget() is self.install_slot

    def show_job(self):
        self.preview_card.hide()
        if hasattr(self, 'install_slot'):
            self.install_slot.hide()
        self.job_slot.show()
        self.job_card.show()

    @staticmethod
    def crystal_rows(panel):
        """The rows of the panel in the order of the molecule page — (main rows of the form, rows of
        «Дополнительные настройки…» with their groups). The titles of the panel's own rows (panel.rows) find the rows
        made inside it (the supercell, the resources)."""
        made = {title: widget for title, widget in panel.rows()}
        main = [
            (tr('Программа'), panel.program_box),
            (tr('Задача'), panel.task),
            (tr('Метод'), panel.functional_line),  # Quantum ESPRESSO: the functional (and the download of its library)
            (tr('Метод'), panel.cp2k_functional),  # CP2K: the functional or GFN1-xTB
            (tr('Базис'), panel.basis),  # CP2K: MOLOPT
            (tr('Обрезки'), panel.cut_auto),  # Quantum ESPRESSO: the plane waves — its «basis»
            ('', panel.cut_line),
            (tr('Сетка плотности'), panel.cp2k_cut_line),
            (tr('Дисперсия'), panel.vdw),
            (tr('Дисперсия'), panel.cp2k_vdw),
            (tr('Ресурсы'), made[tr('Ресурсы')]),
            # the rows of the task and of the crystal (on the molecule page — the rows of the task under the main ones)
            (tr('Сетка k'), panel.k_line),
            ('', panel.grid_line),
            (tr('Ячейка'), panel.primitive),
            (tr('Суперячейка'), made[tr('Суперячейка')]),
            (tr('Пороги оптимизации'), panel.relax_line),
        ]
        extra = [
            (tr('Электронное состояние'), None),
            (tr('Заряд ячейки'), panel.charge),
            (tr('Спин'), panel.spin),
            ('', panel.spin_line),
            ('DFT+U', panel.hubbard),
            (tr('SCF и заполнение'), None),
            (tr('Заполнение'), panel.occupations),
            ('', panel.smear_line),
            ('', panel.temperature_line),
            (tr('Сходимость SCF'), panel.conv),
            (tr('Сходимость SCF'), panel.eps_scf),
        ]
        return main, extra

    def align_with_molecule(self):
        """The captions of «Постановка задачи» of the crystal and of the molecule — one column width, so
        that the fields of both pages start at one place (azimuth.ui.align_form_labels)."""
        from azimuth.ui import align_form_labels

        panel = self.panel
        if panel is None or getattr(panel, 'form', None) is None:
            return 0
        molecule = self.w.main_form if self.w.has('main_form') else None
        return align_form_labels(panel.form, molecule)

    def show_setup_fields(self):
        """The menu of «Поля…»: the fields shown in the card of the crystal."""
        menu = self.setup_rows.menu(self.fields_button)
        menu.exec(self.fields_button.mapToGlobal(self.fields_button.rect().bottomLeft()))
        return menu

    def show_options(self):
        self.options_dialog.show()
        self.options_dialog.raise_()
        self.options_dialog.activateWindow()
        return self.options_dialog

    def update_options_summary(self):
        """The line next to «Дополнительные настройки…»: what is set there (as on the molecule page)."""
        panel = self.panel
        if panel is None or not hasattr(self, 'options_summary'):
            return ''
        cp2k = panel.program == 'cp2k'
        parts = [tr('заряд {:+d}').format(panel.charge.value()) if panel.charge.value() else tr('заряд 0')]
        if panel.spin.isChecked():  # with its order
            parts.append(tr('спин: {}').format(panel.order.currentText()))
        if panel.hubbard.text().strip():
            parts.append('U: ' + panel.hubbard.text().strip())
        parts.append(panel.occupations.currentText())
        parts.append((panel.eps_scf if cp2k else panel.conv).currentText())
        text = ' · '.join(parts)
        self.options_summary.setText(text)
        return text

    def job_event(self, event, panel):
        """The job of the panel started, went on or ended — the card in the place of the input file follows."""
        import time

        card = self.job_card
        if event == 'start':
            task = panel.task.currentData()
            where = tr('сервер') if panel.on_server() else tr('этот компьютер')
            card.begin(f"{'CP2K' if panel.program == 'cp2k' else 'Quantum ESPRESSO'} · {panel.name}", f'{tr(task)} · {panel.processes.value()} ' + tr('проц.') + f' · {where}')
            card.stop_button.setEnabled(True)
            card.output_button.setEnabled(True)
            card.folder_button.setEnabled(True)
            self._started_at = time.monotonic()
            self.show_job()
            return
        text = panel.job.text() if panel.job is not None else ''
        spent = int(time.monotonic() - getattr(self, '_started_at', time.monotonic()))
        when = f'{spent // 60}:{spent % 60:02d}'
        for key, mark, words in (CP2K_STAGES if panel.program == 'cp2k' else STAGES):
            if mark in text and (key != 'molden' or (panel.folder is not None
                                                     and (panel.folder / 'azimuth-MOS-1_0.molden').exists())):
                card.add_stage(key, tr(words), when)
        card.status.setText(panel.status.text())
        if event == 'end':
            card.finish()
            card.stop_button.setEnabled(False)
            ok = panel.result is not None and panel.result.done and not panel.result.error
            card.show_picture('calc-done' if ok else 'calc-failed')
            if ok:
                card.status.setText(panel.summary.text())
            card.show_results(compass=ok, spectrum=ok)
            # another crystal tab chosen during the run — now it is put on the page (the card of the job
            # keeps the result of the run that ended)
            tab = getattr(self.w, 'crystal', None)
            if self.active and tab and tab[0] is not panel.crystal:
                from PySide6.QtCore import QTimer

                QTimer.singleShot(0, self.enter)

    def set_where(self, key):
        """The switch chosen: the server needs a profile — «Сервер…» opens when there is none."""
        panel = self.panel
        if key == 'server' and panel.server_profile() is None:
            try:
                self.w.run_tool.edit_server()
            except Exception as exc:  # noqa: BLE001 — the dialog is the window's; its failure keeps this computer
                self.w.notify(str(exc), 8000)
            panel.update_where()
        index = panel.where.findData(key)
        if index >= 0:
            panel.where.setCurrentIndex(index)
        self.sync_where()

    def sync_where(self):
        key = self.panel.where.currentData() or 'local'
        if key in self.where_buttons:
            self.where_buttons[key].setChecked(True)
        for item in (getattr(self, 'server_button', None), getattr(self, 'server_files_button', None)):
            if item is not None:
                item.setVisible(key == 'server')

    def edit_server(self):
        """«Сервер…» of the crystal page: the profile of the server; its new name or address shown in the list."""
        try:
            self.w.run_tool.edit_server()
        except Exception as exc:  # noqa: BLE001 — the dialog is the window's
            self.w.notify(str(exc), 8000)
        self.panel.update_where()
        self.sync_where()

    def leave(self):
        if self.page is not None:
            self.w.calc_stack.setCurrentWidget(self.w.calc_body)
        self.active = False

    # -- a project of no kind yet — the programs of both kinds -------------------------------------------
    # Until a file is opened, a new project is neither of a crystal nor of molecules, so Sextant offers the programs of
    # both. The list of programs of the molecule page gets, under
    # a separator, the programs of a crystal; one of them chosen opens a CIF (the project becomes a crystal one) and
    # its page with that program. The list of the molecule programs stays chosen meanwhile (program_changed).
    CRYSTAL_PROGRAMS = (('qe', 'Quantum ESPRESSO — кристалл (CIF)'), ('cp2k', 'CP2K — кристалл (CIF)'))

    def sync_programs(self):
        combo = getattr(self.w, 'program', None)
        if combo is None:
            return False
        want = self.w.project_kind() == ''
        have = combo.findData('qe') >= 0
        if want != have:
            combo.blockSignals(True)
            if want:
                from azimuth.ui import thin_separators

                thin_separators(combo)  # a thin line between the programs of molecules and of crystals
                combo.insertSeparator(combo.count())
                for key, title in self.CRYSTAL_PROGRAMS:
                    combo.addItem(tr(title), key)
            else:
                for key, _ in self.CRYSTAL_PROGRAMS:
                    combo.removeItem(combo.findData(key))
                last = combo.count() - 1
                if last >= 0 and combo.itemData(last, Qt.ItemDataRole.AccessibleDescriptionRole) == 'separator':
                    combo.removeItem(last)
            combo.blockSignals(False)
        return want

    def crystal_program_chosen(self, kind, back):
        """A program of a crystal chosen in the list of the molecule page: the list goes back to «back» (the index of
        the molecule program), a CIF is opened; a crystal opened — the page of the crystal with that program."""
        combo = self.w.program
        combo.blockSignals(True)
        combo.setCurrentIndex(back)
        combo.blockSignals(False)
        if not self.w.crystal_tool.open_cif():
            return False
        if getattr(self.w, 'crystal', None) is None:
            return False
        self.w.navigate(1)  # Sextant of the crystal tab: its page
        if self.panel is not None:
            self.panel.set_program(kind)
        return True

    def follow(self, document):
        """A crystal tab — its calculation; a molecule tab (None) — the page of the molecule."""
        if document is not None:
            return self.enter(document)
        if self.active:
            self.leave()
        return False
