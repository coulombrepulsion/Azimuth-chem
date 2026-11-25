"""Project tabs and a shared molecule sidebar for Compass, Sextant and Spectrum.

Contract: a tab owns one portable project folder, including an unsaved draft. Internal Document objects remain
per-molecule so their editing state, program, output and asynchronous job targets keep stable identities. Opening
a structure file starts a project; dropping/adding files appends to the active project. No calculation is submitted
by opening, selecting, saving or preparing. A draft is retained until its files have been copied to a permanent
folder; running project folders are never moved. The sidebar is outside Studio's three-page stack, so it follows
all scientific sections and disappears with Studio on the home page. Programmatic legacy document operations remain usable.

The class is put together from parts: the widgets — azimuth/project_widgets.py; the crystals —
project_crystals.py; the columns and conformers of the list — project_rows.py; moving and removing molecules —
project_moves.py; saving, naming and drafts — project_saving.py. Here: building the panel, refreshing it, the
tabs, the menu of the molecules, reactions, the sliding panel and the results.
"""


from azimuth.i18n import tr
from azimuth.project_crystals import ProjectCrystals
from azimuth.project_rows import ProjectRows
from azimuth.project_moves import ProjectMoves
from azimuth.project_saving import ProjectSaving
from azimuth.project_widgets import (
    COLUMNS,
    COLUMN_TIPS,
    GAP,
    NEW_ROW,
    PlusDrops,
    _FoldClicks,
    _list_keys,
    even_step,
    molecule_table,
    project_tab_bar,
    slide_box,
    slide_log_start,
    slide_log_step,
    slide_profile_begin,
    slide_profile_end,
)
from azimuth import project_tabs as _tabs
from azimuth import project_menus as _menus
from azimuth import project_results as _results


class ProjectNavigation(ProjectCrystals, ProjectRows, ProjectMoves, ProjectSaving):
    def install_project_navigation(self, body):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QTabBar, QFrame, QLabel
        from azimuth.icons import iconify
        from azimuth.ui import button

        self.project_sessions = []
        self.project_last_molecule = {}
        self.project_empty_documents = {}
        self.project_new_documents = {}  # «Новая молекула» — the empty molecule waiting in the list of a project
        # (by the id of the project — its folder is renamed after its first molecule, auto_name_project)
        self.crystal_documents = {}  # the project of a crystal (its project.qcc) -> its tab of «Кристалл»
        self.project_tabs = project_tab_bar()  # molecules dragged onto a tab go into its project
        self.project_tabs.setObjectName('documents')
        self.project_tabs.setExpanding(False)
        self.project_tabs.setTabsClosable(True)
        self.project_tabs.setDocumentMode(True)
        self.project_tabs.setUsesScrollButtons(True)
        self.project_tabs.addTab(tr('Новый проект'))  # no icon until a molecule or a crystal is in it
        self.project_tabs.currentChanged.connect(self.activate_project_tab)
        self.project_tabs.setMovable(True)
        self.project_tabs.tabMoved.connect(self.project_tab_moved)
        self.project_tabs.tabCloseRequested.connect(self.close_project_tab)
        shell = QWidget()
        outer = QVBoxLayout(shell)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        bar = QHBoxLayout()
        # its own sign — ☰ (trajectory_button) stays the drawer of the result in Compass
        self.project_menu_button = iconify(button('', self.toggle_project_molecules), 'molecule-list', tr('Молекулы проекта'))
        self.project_menu_button.setCheckable(True)
        self.project_menu_button.setFixedSize(28, 28)
        bar.addWidget(self.project_menu_button)
        bar.addWidget(self.project_tabs)
        plus = iconify(button('', lambda: self.new_project_from_plus()), 'plus', tr('Новый проект'))
        plus.setFixedSize(26, 26)
        # the rows of the list dropped on «+» — a new project of them (⌥ / Alt — copied)
        plus.setAcceptDrops(True)
        self._plus_drops = PlusDrops(plus, lambda: self.project_molecules,
                                     lambda copy: self.molecules_to_new_project(copy=copy))
        plus.installEventFilter(self._plus_drops)
        self.new_project_plus = plus
        bar.addWidget(plus)
        bar.addStretch(1)
        outer.addLayout(bar)
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)  # the panel slides; a gap would stay when it is closed
        # the list as the page «Структуры» of the drawer — the card title, the name of the project under it, the table
        # №, Структура, Формула; the icons of the head as the drawer has them; the actions under the table
        from modules.compass.panels.trajectory_drawer import WIDTH

        self.project_pane = QFrame()
        # a card of its
        # own — rounded 12 px, outlined; the drawer of Compass keeps its straight corners (it lies over the field)
        self.project_pane.setObjectName('projectPane')
        self.project_pane.setFixedWidth(WIDTH)
        left = QVBoxLayout(self.project_pane)
        left.setContentsMargins(16, 14, 14, 14)
        left.setSpacing(9)
        head = QHBoxLayout()
        head.setSpacing(2)
        self.project_title = QLabel(tr('Структуры'))
        self.project_title.setObjectName('cardtitle')
        head.addWidget(self.project_title, 1)
        self.project_add_button = iconify(button('', self.add_project_files_dialog), 'plus', tr('Добавить молекулы…'))
        self.project_history_button = iconify(button('', self.show_research_project), 'history',
                                              tr('История и файлы проекта…'))
        self.project_close_button = iconify(button('', self.hide_project_molecules), 'close', tr('Закрыть панель'))
        for item in (self.project_add_button, self.project_history_button, self.project_close_button):
            item.setFixedSize(28, 28)
            head.addWidget(item)
        left.addLayout(head)
        self.project_caption = QLabel(tr('Молекулы'))
        self.project_caption.setObjectName('subtitle')
        self.project_caption.setWordWrap(True)
        left.addWidget(self.project_caption)
        # «Одиночный» — the molecule chosen in the list
        # is calculated, analysed, made 3D; «Пакетный» — all the molecules with a tick (all of them at first; a tick
        # taken off leaves one out): the queue of Sextant, QTAIM of Spectrum, «Сделать 3D» take them. The row chosen is
        # still the molecule shown. The mode and the ticks are kept in project.qcc. No buttons under the table.

        self.project_mode_tabs = QTabBar()
        self.project_mode_tabs.setObjectName('viewTabs')
        self.project_mode_tabs.setDrawBase(False)
        self.project_mode_tabs.setExpanding(False)
        self.project_mode_tabs.addTab(tr('Одиночный'))
        self.project_mode_tabs.addTab(tr('Пакетный'))
        self.project_mode_tabs.setTabToolTip(0, tr('Расчёты и анализ — для молекулы, выбранной в списке'))
        self.project_mode_tabs.setTabToolTip(1, tr('Расчёты и анализ — для всех отмеченных молекул; снимите галочку, '
                                                   'чтобы исключить молекулу'))
        self.project_mode_tabs.currentChanged.connect(lambda index: self.set_project_batch_mode(index == 1))
        left.addWidget(self.project_mode_tabs)
        self.project_molecules = molecule_table()
        # several rows may be chosen (Shift, Cmd) — to remove them together; the current row is the molecule shown
        self.project_molecules.setSelectionMode(self.project_molecules.SelectionMode.ExtendedSelection)
        self.project_molecules.currentCellChanged.connect(lambda row, *_: self.project_molecule_chosen(row))
        self.project_molecules.itemChanged.connect(self.project_tick_changed)
        self.project_molecules.on_rows_moved = self.move_project_molecules
        self.project_molecules.hover_at = self.molecules_hover  # several rows carried by the program
        self.project_molecules.drop_at = self.molecules_drop
        self.project_tabs.source = self.project_molecules  # rows dragged onto another project's tab
        self.project_tabs.accepts = self.project_tab_takes_molecules
        self.project_tabs.on_molecules_dropped = lambda index, copy: self.molecules_to_project_tab(index, copy=copy)
        self._fold_clicks = _FoldClicks(self.project_molecules, self.toggle_conformers)  # ▸ / ▾
        self.project_molecules.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_molecules.customContextMenuRequested.connect(self.project_molecules_menu)
        heads = self.project_molecules.horizontalHeader()  # the columns chosen and their widths
        heads.customContextMenuRequested.connect(self.project_columns_menu)
        heads.sectionResized.connect(self.project_column_resized)
        for column, (key, _, _) in enumerate(COLUMNS):
            if key in COLUMN_TIPS:
                self.project_molecules.horizontalHeaderItem(column).setToolTip(tr(COLUMN_TIPS[key]))
        self.apply_project_columns()
        self._project_removed = None  # (path, [(position, entry)]) of the last removal, files kept
        # Delete / ⌫ in the list removes; Ctrl+Z (⌘Z) there puts back — taken before the shortcuts of the window
        # («Удалить выбранные атомы (Delete)», «Отменить»), which would act on the model instead
        self._project_keys = _list_keys(self)
        self.project_molecules.installEventFilter(self._project_keys)
        left.addWidget(self.project_molecules, 1)
        self.project_slide = slide_box(self.project_pane)  # slides out and back as the drawer of Compass
        self.project_motion = None
        row.addWidget(self.project_slide)
        body.removeWidget(self.stack)
        row.addWidget(self.stack, 1)
        outer.addLayout(row, 1)
        body.addWidget(shell, 1)
        self.align_spectrum_tabs()
        # Batch analysis is available on the existing Bader/QTAIM page, including when no single result is selected.
        # one button, shown in the batch mode — the molecules with a tick (the single mode has the page itself)
        self.project_qtaim_button = button(tr('QTAIM отмеченных молекул'),
                                           lambda: self.project_qtaim(self.selected_project_molecules()))
        self.project_qtaim_button.setToolTip(tr('Тот же поиск критических точек (Multiwfn), но сразу для всех молекул '
                                                'проекта с галочкой — по одной после другой; общие таблицы — в «Анализе» '
                                                'проекта. «Найти критические точки» — только для показанного результата.'))
        self.project_qtaim_button.hide()
        # beside it, in the row of the search (it stood in a row of its own over the panel)
        row = self.topology_panel.aim_row
        row.insertWidget(row.indexOf(self.topology_panel.model_button) + 1, self.project_qtaim_button)

    def align_spectrum_tabs(self):
        """The tabs of the result (Обзор, ИК, …) go inside the panel of Spectrum, first, as «Молекула | Координаты» in
        Compass: the panel then begins level with the list of the project and the pages of Compass and Sextant."""
        top = getattr(self, 'result_top_row', None)
        panel = getattr(self, 'result_panel', None)
        if top is None or panel is None or panel.layout() is None:
            return
        holder = top.parentWidget()
        if holder is not None and holder.layout() is not None:
            holder.layout().removeWidget(top)
        top.setParent(panel)
        # as the row of Compass (documents.build_view_row), 12 px in — past the rounded corner of the panel of
        # the group under the tabs, where its straight edge begins
        top.layout().setContentsMargins(12, 0, 2, 0)
        layout = panel.layout()
        layout.insertWidget(0, top)
        top.show()
        # no room between the tabs and
        # the panels of the page under them; the status lines at the foot keep theirs
        layout.setSpacing(0)
        for k in range(layout.count()):
            item = layout.itemAt(k)
            if item.layout() is not None and item.layout() is not getattr(self.result_tabs, 'layout', lambda: None)():
                layout.insertSpacing(k, 10)  # before the status row (the only layout among the items)
                break
        for i in range(self.result_tabs.count()):
            inner = self.result_tabs.widget(i).layout()
            if inner is not None and self.result_tabs.widget(i).objectName() != 'resultCard':
                margins = inner.contentsMargins()
                inner.setContentsMargins(margins.left(), 0, margins.right(), margins.bottom())

    register_project_tab = _tabs.register_project_tab
    refresh_project_navigation = _tabs.refresh_project_navigation
    projects_root = _tabs.projects_root
    choose_projects_folder = _tabs.choose_projects_folder
    new_project_tab = _tabs.new_project_tab
    new_crystal_side_project = _tabs.new_crystal_side_project
    project_kind = _tabs.project_kind
    ensure_project_tab = _tabs.ensure_project_tab
    loose_molecule_document = _tabs.loose_molecule_document
    keep_loose_molecule = _tabs.keep_loose_molecule
    activate_loose_tab = _tabs.activate_loose_tab
    new_project_from_plus = _tabs.new_project_from_plus
    activate_project_tab = _tabs.activate_project_tab
    close_project_tab = _tabs.close_project_tab
    selected_project_molecules = _menus.selected_project_molecules
    chosen_project_rows = _menus.chosen_project_rows
    project_molecules_menu = _menus.project_molecules_menu
    project_attempt_count = _menus.project_attempt_count
    show_molecule_history = _menus.show_molecule_history
    add_reaction_actions = _menus.add_reaction_actions
    set_reaction_role = _menus.set_reaction_role
    ask_reaction_coefficient = _menus.ask_reaction_coefficient
    project_reaction = _menus.project_reaction
    project_calculation_folder = _menus.project_calculation_folder
    open_project_calculation_folder = _menus.open_project_calculation_folder
    project_tick_changed = _menus.project_tick_changed
    project_plan_changed = _menus.project_plan_changed
    sync_project_plan = _menus.sync_project_plan

    def project_molecule_chosen(self, row, previous=None):
        if getattr(self, '_project_refreshing', False) or row is None or row < 0:
            return
        from azimuth.tasks import held

        if held():  # a work goes on in the molecule shown — another one is opened after it
            return
        from PySide6.QtCore import Qt
        cell = self.project_molecules.item(row, 0)
        if cell is None:
            return
        ident = cell.data(Qt.ItemDataRole.UserRole)
        if isinstance(ident, str) and (ident == 'crystal' or ident.startswith('crystal:')):
            self.choose_project_crystal(ident)  # another crystal of the project; the one shown — nothing
            return
        if ident == NEW_ROW:  # back to the empty molecule of «Новая молекула»
            pending = self.pending_project_molecule()
            if pending is not None:
                self.save_research_project()
                self.switch_document(self.documents.index(pending))
                self.refresh_project_navigation()
            return
        self.save_research_project()
        section = self.stack.currentIndex()
        self.open_project_molecule(ident, stay=True)
        if self.stack.currentIndex() != section:
            self.navigate(section)
        self.project_last_molecule[str(self.research_path())] = ident
        self.project_section_changed(self.stack.currentIndex())

    def toggle_project_molecules(self):
        opened = self.project_menu_button.isChecked()
        if opened:  # the list is read again when the panel comes out, not when it goes away
            self.ensure_project_tab()
            self.refresh_project_navigation()
        self.slide_project_pane(opened)

    def hide_project_molecules(self):
        """✕ of the head, as the drawer closes."""
        self.project_menu_button.setChecked(False)
        self.slide_project_pane(False)

    def _project_slide_step(self, width):
        """One step of the slide — the width, the layout at once (not on the next turn of the loop: for a
        frame the panel and the field overlapped or left a gap), the field drawn at once (viewer.layout_motion)."""
        box = self.project_slide
        if box.width() == width:
            return
        started = slide_log_start()
        viewer = getattr(self, 'viewer', None)
        if viewer is not None and hasattr(viewer, 'layout_motion'):
            viewer.layout_motion()
        box.setFixedWidth(width)
        holder = box.parentWidget()
        if holder is not None and holder.layout() is not None:
            holder.layout().activate()
        slide_log_step(started, width)

    def project_pane_open(self):
        return self.project_slide.isVisible() and self.project_slide.width() > 0 and (
            self.project_motion is None or self.project_motion.endValue() > 0)

    def slide_project_pane(self, opened, animate=True):
        """The panel of the molecules comes out (OutCubic) and goes back (InOutCubic) in SLIDE_MS, the curves
        and the time of the drawer of Compass; at once when the window is not shown."""
        from PySide6.QtCore import QEasingCurve, QVariantAnimation
        from modules.compass.panels.trajectory_drawer import SLIDE_MS

        box = self.project_slide
        target = self.project_pane.width() + GAP if opened else 0
        if self.project_motion is not None:
            self.project_motion.stop()
            self.project_motion = None
        if opened:
            box.show()
        viewer = getattr(self, 'viewer', None)
        if not animate or not self.isVisible() or box.width() == target:
            box.setFixedWidth(target)
            box.setVisible(bool(target))
            if viewer is not None and hasattr(viewer, 'end_glide'):
                viewer.end_glide()
            return
        if viewer is not None and hasattr(viewer, 'begin_glide'):
            viewer.begin_glide()  # the field slides as one picture, drawn anew when the panel stops
        motion = QVariantAnimation(self)
        motion.setDuration(SLIDE_MS)
        # out the same smooth curve as back, its steps no larger than 1.5 times the mean
        motion.setEasingCurve(QEasingCurve.Type.InOutCubic)
        motion.setStartValue(box.width())
        motion.setEndValue(target)
        motion.valueChanged.connect(lambda value: self._project_slide_step(even_step(value)))

        from azimuth.ui import freeze_ornaments

        freeze_ornaments(self)  # the scales of the window a picture while the panel slides
        profiled = slide_profile_begin()

        def done():
            slide_profile_end(profiled, 'Молекулы проекта')
            freeze_ornaments(self, False)
            box.setFixedWidth(target)
            box.setVisible(bool(target))
            if self.project_motion is motion:
                self.project_motion = None
                if viewer is not None and hasattr(viewer, 'end_glide'):
                    holder = box.parentWidget()
                    if holder is not None and holder.layout() is not None:
                        holder.layout().activate()  # the field at its last size before the model is drawn
                    viewer.end_glide()

        motion.finished.connect(done)
        self.project_motion = motion
        motion.start()

    def show_project_molecules(self):
        self.project_menu_button.setChecked(True)
        self.toggle_project_molecules()

    def project_section_changed(self, index):
        if not hasattr(self, 'project_tabs'):  # before the navigation is built
            return
        if self.research_path():
            self.attach_project_placeholder()
            self.result_tabs.setTabVisible(self.topology_tab, True)
            if index in (0, 2):  # in Compass too — the steps and vibrations of its result in the drawer (☰)
                self.show_project_result()
        if hasattr(self, 'trajectory_tool'):  # ☰ of the result shown when there is one
            self.trajectory_tool.update_result_button()

    show_project_result = _results.show_project_result
    load_project_conformers = _results.load_project_conformers
    say_result_mismatch = _results.say_result_mismatch
    project_result_properties = _results.project_result_properties
    project_queue_row_ended = _results.project_queue_row_ended
    open_project_topology = _results.open_project_topology
    open_project_compass_result = _results.open_project_compass_result
    prepare_whole_project = _results.prepare_whole_project
    prepare_selected_project = _results.prepare_selected_project
    add_project_files_dialog = _results.add_project_files_dialog
    open_files_project = _results.open_files_project
