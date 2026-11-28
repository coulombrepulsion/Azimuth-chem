"""The page of Spectrum: the tabs of the result (ResultTabs over WholeTabBar), the cards, the pill of the status.
results_page is a method of SpectrumWorkspace (self is the window), kept here to make workspace.py shorter.

Split off modules/spectrum/workspace.py (0.222.29).
"""

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QTableWidget,
    QHeaderView,
    QTabWidget,
    QTabBar,
    QLabel,
    QSizePolicy,
)
from PySide6.QtCore import QEvent, QObject, Qt
from modules.spectrum.views.vibrations import VibrationPanel
from azimuth import quill
from azimuth.ui import label, button, card
from azimuth.icons import iconify
from azimuth.i18n import tr


EMPTY_RESULT = ('В этой вкладке результата ещё нет. Откройте вывод программы (.out, .log) — Спектр выделит энергию, '
                'частоты и признаки завершения.')  # one place for the empty state (the hint was on top)
TAB_MARGINS = (0, 10, 0, 0)  # inside every tab of the result; the panel has its margins already


class WholeTabBar(QTabBar):
    """A tab bar exactly as wide as all its visible tabs. The row squeezed it to scroll arrows, and a size
    hint that grew while Spectrum was hidden did not reach the layout (the user's Mac: 159 px for 416 px of tabs) —
    so the width is set outright (fit) whenever the tabs change and when the bar is shown."""

    def fit(self):
        width = sum(self.tabSizeHint(i).width() for i in range(self.count()) if self.isTabVisible(i))
        self.setFixedWidth(max(1, width))

    def showEvent(self, event):
        super().showEvent(event)
        self.fit()


CARD_MARGINS = (14, 12, 14, 14)  # inside a page of a result framed as a card


def framed(panel):
    """A page of a result drawn as a card (QWidget#resultCard: the white of a card, its outline and radius,
    app.py) with the margins of one."""
    panel.setObjectName('resultCard')
    panel.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
    if panel.layout() is not None:
        panel.layout().setContentsMargins(*CARD_MARGINS)
    return panel


class ResultTabs(QTabWidget):
    """The tabs of a result shown by a bar of their own (header) placed in the top row of the panel, next to
    the tabs of the molecules (the bar of the tab widget is hidden — it took a row of its own under the file name). The
    tab widget keeps its API for the program and the tests; the header follows its tabs, their visibility and the
    current one, and a click on the header chooses the tab.
    Tabs of a group (set_group) share one tab of the header — the name of the group when two or more
    of them are shown, the tab's own name when one —, and the tabs of the current group are a second bar (subheader)
    over the page; the group opens on the tab chosen there last.
    No second bar — the tabs of the
    group shown are a drop-down list over the page (chooser, as the pages of the drawer of Compass), its title the tab
    shown; the group opens on the tab chosen there last. (subheader stays, hidden, for the API.)"""

    def __init__(self):
        super().__init__()
        self.header = WholeTabBar()
        self.header.setObjectName('viewTabs')  # the style of «Молекула | Координаты» of Compass
        self.header.setExpanding(False)
        self.header.setDrawBase(False)
        # all the tabs of the result always in full: the tabs of the molecules after them give way (they scroll)
        self.header.setUsesScrollButtons(False)
        self.header.setElideMode(Qt.TextElideMode.ElideNone)
        self.header.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.subheader = WholeTabBar()  # the tabs of the group shown
        self.subheader.setObjectName('viewTabs')
        self.subheader.setExpanding(False)
        self.subheader.setDrawBase(False)
        self.subheader.setUsesScrollButtons(False)
        self.subheader.setElideMode(Qt.TextElideMode.ElideNone)
        self.subheader.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Preferred)
        self.subheader.setParent(self)
        self.subheader.hide()
        from PySide6.QtWidgets import QComboBox

        self.chooser = QComboBox()  # the tabs of the group shown, in place of the second bar
        self.chooser.setObjectName('drawerPages')
        self.chooser.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToContents)
        self.chooser.setMinimumWidth(240)
        self.chooser.hide()
        self.groups = {}  # widget → the title of its group
        self.last_of = {}  # the title of a group → the widget chosen there last
        self.entries = []  # one per tab of the header: (title, [indices of the tabs shown])
        self.tabBar().hide()
        self.setDocumentMode(True)
        self.header.currentChanged.connect(self._header_chosen)
        self.subheader.currentChanged.connect(self._sub_chosen)
        self.chooser.activated.connect(self._sub_chosen)
        self.currentChanged.connect(self._follow)

    def _bar(self):
        """The header while both are alive — when the window is deleted the header (a child of the top row)
        may go first, and Qt still calls tabRemoved and currentChanged of the tab widget (a segmentation fault in the
        tests of the hub, which make and delete windows)."""
        from shiboken6 import isValid

        bar = getattr(self, 'header', None)
        sub = getattr(self, 'subheader', None)
        chooser = getattr(self, 'chooser', None)
        alive = all(w is not None and isValid(w) for w in (bar, sub, chooser)) and isValid(self)
        return bar if alive else None

    def group(self):
        """One panel (QFrame#resultGroup, app.py) holding the list of the pages of the group (chooser) over
        the page — the title of the subsection and its cards together, as the drawer of Compass."""
        from PySide6.QtWidgets import QFrame, QVBoxLayout

        if getattr(self, '_group', None) is None:
            frame = QFrame()
            frame.setObjectName('resultGroup')
            column = QVBoxLayout(frame)
            column.setContentsMargins(12, 10, 12, 12)
            column.setSpacing(10)
            # the row is a
            # widget of its own (bar), hidden when it has neither the list of the pages nor a tool shown
            self.bar = QWidget()
            top = QHBoxLayout(self.bar)  # the list of the pages; at the right — the tools of the result (tools)
            top.setContentsMargins(0, 0, 0, 0)
            top.setSpacing(8)
            top.addWidget(self.chooser, 0, Qt.AlignmentFlag.AlignLeft)
            top.addStretch(1)
            self.tools = QHBoxLayout()
            self.tools.setSpacing(8)
            top.addLayout(self.tools)
            column.addWidget(self.bar)
            column.addWidget(self, 1)
            self._group = frame
        return self._group

    def set_group(self, index, title):
        """The tab index belongs to the group title (a translated name)."""
        self.groups[self.widget(index)] = title
        self._rebuild()

    def group_of(self, index):
        return self.groups.get(self.widget(index))

    def entry_of(self, index):
        """The number of the tab of the header that holds the tab index (−1 when it is not shown)."""
        return next((k for k, (_, members) in enumerate(self.entries) if index in members), -1)

    def _rebuild(self):
        bar = self._bar()
        if bar is None:
            return
        entries, where = [], {}
        for index in range(self.count()):
            if not self.isTabVisible(index):
                continue
            group = self.group_of(index)
            if group is None:
                entries.append([self.tabText(index), [index]])
            elif group in where:
                entries[where[group]][1].append(index)
            else:
                where[group] = len(entries)
                entries.append([group, [index]])
        self.entries = [(title if len(members) > 1 else self.tabText(members[0]), members) for title, members in entries]
        bar.blockSignals(True)
        while bar.count():
            bar.removeTab(0)
        for title, _ in self.entries:
            bar.addTab(title)
        bar.blockSignals(False)
        bar.fit()
        self._follow(self.currentIndex())

    def tabInserted(self, index):
        super().tabInserted(index)
        self._rebuild()

    def tabRemoved(self, index):
        super().tabRemoved(index)
        self._rebuild()

    def setTabVisible(self, index, visible):
        super().setTabVisible(index, visible)
        self._rebuild()

    def setTabText(self, index, text):
        super().setTabText(index, text)
        self._rebuild()

    def _header_chosen(self, k):
        from shiboken6 import isValid

        if not isValid(self) or not 0 <= k < len(self.entries):
            return
        members = self.entries[k][1]
        if self.currentIndex() in members:
            return
        last = self.last_of.get(self.group_of(members[0]))
        target = next((i for i in members if self.widget(i) is last), members[0])
        self.setCurrentIndex(target)

    def _sub_chosen(self, k):
        from shiboken6 import isValid

        entry = self.entry_of(self.currentIndex())
        if not isValid(self) or entry < 0 or not 0 <= k < len(self.entries[entry][1]):
            return
        target = self.entries[entry][1][k]
        if target != self.currentIndex():
            self.setCurrentIndex(target)

    def _follow(self, index):
        bar = self._bar()
        if bar is None:
            return
        entry = self.entry_of(index)
        bar.blockSignals(True)
        bar.setCurrentIndex(entry)
        bar.blockSignals(False)
        sub = self.subheader
        members = self.entries[entry][1] if entry >= 0 else []
        sub.blockSignals(True)
        while sub.count():
            sub.removeTab(0)
        if len(members) > 1:
            for i in members:
                sub.addTab(self.tabText(i))
            sub.setCurrentIndex(members.index(index))
            self.last_of[self.group_of(index)] = self.widget(index)
        sub.blockSignals(False)
        sub.hide()
        chooser = self.chooser  # the drop-down list of the group instead of the second bar
        chooser.blockSignals(True)
        chooser.clear()
        for i in members if len(members) > 1 else ():
            chooser.addItem(self.tabText(i))
        if len(members) > 1:
            chooser.setCurrentIndex(members.index(index))
        chooser.blockSignals(False)
        chooser.setVisible(len(members) > 1)
        if callable(getattr(self, 'bar_follows', None)):
            self.bar_follows()


def results_page(self):
    page = QWidget()
    outer = QVBoxLayout(page)
    outer.setContentsMargins(0, 0, 0, 0)
    outer.setSpacing(0)
    # a slim row on the top edge of the panel — the tabs of the result, a thin rule, the tabs
    # of the molecules with «+» (every tab has its own result); the panel right under it; the actions and
    # the status in one line at its foot
    self.result_tabs = ResultTabs()
    from PySide6.QtWidgets import QFrame

    top = QFrame()
    top.setObjectName('documentRow')
    self.result_top_row = top  # moved onto the top of the panel when the tabs are projects
    tabs_row = QHBoxLayout(top)
    tabs_row.setContentsMargins(12, 0, 2, 0)
    tabs_row.setSpacing(2)
    tabs_row.addWidget(self.result_tabs.header, 0, Qt.AlignmentFlag.AlignBottom)
    tabs_row.addStretch(1)  # the row of the molecule tabs after a rule is gone
    outer.addWidget(top)
    self.result_panel, layout = card('')
    heading = layout.itemAt(0).widget()
    layout.removeWidget(heading)
    heading.deleteLater()
    layout.setSpacing(10)
    layout.setContentsMargins(14, 12, 14, 12)  # less empty room between the frames (was 22 × 20)
    outer.addWidget(self.result_panel, 1)
    # the actions in the
    # row of the list of the pages, at its right; the orbitals and the way to Compass only on the pages of «Волновая
    # функция», the reaction diagram on those of «Результат» (the energies it takes) — refresh_result_tools
    group_top = self.result_tabs.group()
    toolbar = self.result_tabs.tools
    self.wave_tools = QWidget()
    wave_row = QHBoxLayout(self.wave_tools)
    wave_row.setContentsMargins(0, 0, 0, 0)
    wave_row.setSpacing(8)
    self.energy_tools = QWidget()
    energy_row = QHBoxLayout(self.energy_tools)
    energy_row.setContentsMargins(0, 0, 0, 0)
    energy_row.setSpacing(8)
    # orbitals from the Molden file next to the output (orca_2mkl <name> -molden)
    self.orbitals_button = button(tr('Орбитали…'), self.open_sibling_orbitals)
    self.orbitals_button.setVisible(False)
    self.orbitals_button.setToolTip(
        tr(
            'Орбитали из вывода (print[p_mos] 1 и print[p_basis] 2) или из файла рядом с ним: '
            'имя.molden.input (orca_2mkl имя -molden), имя.molden, имя.fchk'
        )
    )
    self.sibling_molden = None
    wave_row.addWidget(self.orbitals_button)
    # the same orbitals next to the Compass model (no big window over everything); in the drawer
    # an icon — the way to Compass, like «Перейти в Спектр» of the panel there
    self.density_compass_button = iconify(button('', lambda: self.density_tool.open_density_drawer(tab=0)), 'compass',
                                          tr('Перейти в Компас · орбитали и электронная плотность — во вкладках '
                                             'панели слева от модели'))
    self.density_compass_button.setVisible(False)
    wave_row.addWidget(self.density_compass_button)
    toolbar.addWidget(self.wave_tools)
    # the energy diagram of a reaction from several results (modules/spectrum/views/reaction_view.py)
    self.reaction_button = button(tr('В диаграмму реакции'), self.add_result_to_reaction)
    self.reaction_button.setToolTip(tr('Добавить этот результат стадией в «Диаграмму реакции»'))
    self.reaction_button.setEnabled(False)
    self.reaction_button.setVisible(False)  # shown only for a result with an energy
    energy_row.addWidget(self.reaction_button)
    toolbar.addWidget(self.energy_tools)
    # the folder «Анализ» of the result (the CSV tables of every analysis) or, before any analysis, its own folder
    self.result_folder_button = iconify(button('', lambda: self.open_result_folder()), 'folder',
                                        tr('Папка результата · таблицы анализов (CSV) и выводы Multiwfn — в «Анализ»'))
    self.result_folder_button.setVisible(False)
    # at the right end of the row of the tabs of the result, not in a row of its own
    tabs_row.addWidget(self.result_folder_button, 0, Qt.AlignmentFlag.AlignVCenter)
    self.result_tabs.bar_follows = self.refresh_tools_bar
    # not in the row any more — a result has its own tab, its geometry is there in Compass; kept for the
    # programs and the tests that use it
    self.use_geometry = button(tr('Взять геометрию из результата'), self.adopt_geometry)
    self.use_geometry.setEnabled(False)
    self.use_geometry.hide()
    self.output_source = label('', 'subtitle')  # the hint how to open a result is in the empty status
    self.result_summary = label(tr(EMPTY_RESULT), 'subtitle')  # the status line at the foot
    self.empty_quill = QLabel()
    self.empty_quill.setObjectName('emptyQuill')
    self.empty_quill.setProperty('quill', True)  # hides the hub's scales
    picture = quill.pixmap('empty-result', 150)
    if not picture.isNull():
        self.empty_quill.setPixmap(picture)
    # the file and the program, then the termination and the energy, on a rounded
    # pill as the message of Compass (QLabel#toast); shown when a result comes, gone after STATUS_MS. Its room
    # stays when it goes, so the page under it does not jump
    from PySide6.QtCore import QTimer
    from PySide6.QtWidgets import QFrame, QSizePolicy

    self.status_pill = QFrame()
    self.status_pill.setObjectName('statusPill')
    policy = self.status_pill.sizePolicy()
    policy.setRetainSizeWhenHidden(True)
    policy.setHorizontalPolicy(QSizePolicy.Policy.Maximum)
    self.status_pill.setSizePolicy(policy)
    status = QVBoxLayout(self.status_pill)  # the file and the program, then the termination and the energy
    status.setContentsMargins(14, 6, 14, 6)
    status.setSpacing(0)
    for line in (self.output_source, self.result_summary):
        line.setWordWrap(False)  # one line each: the pill as wide as its text, not a narrow column
        status.addWidget(line)
    self.status_pill.hide()
    self.status_timer = QTimer(self)
    self.status_timer.setSingleShot(True)
    self.status_timer.timeout.connect(self.status_pill.hide)
    # the pill lies over the foot of the panel of the result (place_status), as the message of Compass over its
    # field — no row of its own under the panel a spectrum being recorded while the calculation runs, at the right
    # of the status line
    from modules.spectrum.views.spectrum_pulse import SpectrumPulse

    self.calc_pulse = SpectrumPulse(getattr(self, 'activities', None))  # over the foot too, at the right
    self.show_empty_quill(True)
    layout.addWidget(group_top, 1)  # the list of the pages and the page, on one panel
    # the optimization steps and the comparison with the start moved to Compass (the ☰ drawer)
    self.result_tabs.currentChanged.connect(self.update_result_geometry)
    self.result_tabs.currentChanged.connect(lambda *_: self.refresh_result_tools())
    records = QWidget()
    records_column = QVBoxLayout(records)
    records_column.setContentsMargins(0, 0, 0, 0)
    # no result yet — Quill and the hint in the card of the frequencies, in place of its table (they took a
    # row at the foot)
    self.empty_page = QWidget()
    empty_column = QVBoxLayout(self.empty_page)
    empty_column.addStretch(1)
    empty_column.addWidget(self.empty_quill, 0, Qt.AlignmentFlag.AlignHCenter)
    self.empty_text = label(tr(EMPTY_RESULT), 'subtitle')
    self.empty_text.setAlignment(Qt.AlignmentFlag.AlignHCenter)
    self.empty_text.setMaximumWidth(520)
    empty_column.addWidget(self.empty_text, 0, Qt.AlignmentFlag.AlignHCenter)
    empty_column.addStretch(1)
    self.records_cards = QWidget()
    row = QHBoxLayout(self.records_cards)
    row.setContentsMargins(0, 0, 0, 0)
    row.setSpacing(12)
    records_column.addWidget(self.records_cards, 1)
    self.result_tabs.addTab(records, tr('Энергии и частоты'))
    card_e, layout_e = card(tr('Энергии · хартри'))
    layout_e.setContentsMargins(14, 12, 14, 14)  # closer to the frame
    self.energy_table = QTableWidget(0, 2)
    self.energy_table.setHorizontalHeaderLabels([tr('Запись'), tr('Энергия')])
    card_f, layout_f = card(tr('Частоты · см⁻¹'))
    layout_f.setContentsMargins(14, 12, 14, 14)
    self.frequency_table = QTableWidget(0, 2)
    self.frequency_table.setHorizontalHeaderLabels([tr('Мода'), tr('Частота')])
    for table, box in [(self.energy_table, layout_e), (self.frequency_table, layout_f)]:
        table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        table.verticalHeader().hide()  # the first column numbers the rows already
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        box.addWidget(table, 1)  # the table fills its card (the frequencies took a third of it)
    layout_f.addWidget(self.empty_page, 1)
    row.addWidget(card_e, 2)  # a few energies, many frequencies
    row.addWidget(card_f, 3)
    self.vibrations = VibrationPanel()
    self.vibrations_tab = self.result_tabs.addTab(self.vibrations, tr('Колебания и ИК'))
    self.result_tabs.setTabVisible(self.vibrations_tab, False)  # only for a result with frequencies
    self.vibrations.displacedRequested.connect(self.adopt_displaced)
    self.vibrations.compassRequested.connect(self.vibration_in_compass)
    from modules.spectrum.views.spectra_view import NMRPanel
    from modules.spectrum.views.uv_view import UVVisPanel

    self.uv_panel = UVVisPanel()
    self.uv_tab = self.result_tabs.addTab(self.uv_panel, tr('UV-Vis'))
    if hasattr(self, 'surface_tool'):  # the hole and the electron of the excited states
        self.uv_panel.set_analysis(self.excitation_source, self.surface_tool.show_excitation)
        self.uv_panel.set_transfer(self.transfer_context)  # the charge transfer between fragments
    if hasattr(self, 'density_tool'):  # the NTOs of a state in the drawer of Compass
        self.uv_panel.set_ntos({}, self.show_nto)
    self.nmr_panel = NMRPanel(getattr(self, 'preferences', None))
    self.nmr_tab = self.result_tabs.addTab(self.nmr_panel, tr('ЯМР'))
    self.nmr_panel.tmsRequested.connect(self.open_tms_input)
    self.result_tabs.setTabVisible(self.uv_tab, False)
    self.result_tabs.setTabVisible(self.nmr_tab, False)
    from modules.spectrum.views.convergence_view import ConvergencePanel
    from modules.spectrum.views.thermo_view import ThermoPanel

    self.thermo_panel = ThermoPanel()
    self.thermo_tab = self.result_tabs.addTab(self.thermo_panel, tr('Термохимия'))
    self.convergence_panel = ConvergencePanel()
    self.convergence_tab = self.result_tabs.addTab(self.convergence_panel, tr('Сходимость'))
    self.result_tabs.setTabVisible(self.thermo_tab, False)
    self.result_tabs.setTabVisible(self.convergence_tab, False)
    from modules.spectrum.views.measured_view import MeasuredPanel  # a molecule of the course next to experiment

    self.measured_panel = MeasuredPanel()
    self.measured_tab = self.result_tabs.addTab(self.measured_panel, tr('Опыт'))
    self.result_tabs.setTabVisible(self.measured_tab, False)
    from modules.spectrum.views.field_view import FieldPanel  # maps in a plane and profiles along a line

    self.field_panel = FieldPanel(lambda: self.property_tool.multiwfn_source() if hasattr(self, 'property_tool') else None,
                                  self.result_geometry, topology=lambda: self.topology_panel.topology)
    self.field_panel.orbitals = self.result_orbitals  # the last map and profile kept, when opened
    self.field_tab = self.result_tabs.addTab(self.field_panel, tr('Карты и профили'))
    self.result_tabs.setTabVisible(self.field_tab, False)
    # the density of states — DOS, PDOS of the elements or of the atoms chosen in Compass, OPDOS
    from modules.spectrum.views.dos_view import DosPanel

    self.dos_panel = DosPanel()
    self.dos_panel.set_source(self.dos_orbitals,
                              (lambda: set(self.viewer.selected)) if hasattr(self, 'viewer') else None)
    self.dos_tab = self.result_tabs.addTab(self.dos_panel, tr('Плотность состояний'))
    self.result_tabs.setTabVisible(self.dos_tab, False)
    # the delocalization indices and the aromaticity of the rings (HOMA here, the rest by Multiwfn)
    from modules.spectrum.views.delocalization_view import DelocalizationPanel

    self.deloc_panel = DelocalizationPanel()
    self.deloc_panel.set_source(self.result_geometry,
                                lambda: self.property_tool.multiwfn_source() if hasattr(self, 'property_tool') else None,
                                self.result_orbitals)  # what was computed for them, when opened
    self.deloc_tab = self.result_tabs.addTab(self.deloc_panel, tr('Делокализация'))
    self.result_tabs.setTabVisible(self.deloc_tab, False)
    self.result_tabs.currentChanged.connect(self.dos_shown)
    self.result_tabs.currentChanged.connect(self.topology_shown)  # the points kept, when it is opened
    self.result_tabs.currentChanged.connect(self.deloc_shown)  # the indices kept, when it is opened
    self.result_tabs.currentChanged.connect(self.field_shown)  # the last map and profile kept
    # the tables and plots of the analysis live in Spectrum — the detailed table of the critical points (the
    # short list stays next to the model) and the plot of NCI (it was a window over Compass)
    from modules.compass.view.nci_plot import NciPanel
    from modules.spectrum.views.density_view import TopologyPanel

    self.topology_panel = TopologyPanel(self.find_result_topology,
                                        (lambda topology, orbitals, title, **kw: self.surface_tool.show_aim(topology, orbitals, title=title, **kw))
                                        if hasattr(self, 'surface_tool') else None)
    if hasattr(self, 'surface_tool'):
        self.topology_panel.clear_aim = self.surface_tool.clear_aim
        self.topology_panel.keep_contacts = self.surface_tool.keep_contacts
        self.topology_panel.aim_shown = lambda: getattr(self.viewer, 'aim', None) is not None
    self.topology_panel.folder_source = self.result_folder  # the tables of the points, in «Анализ»
    self.topology_tab = self.result_tabs.addTab(self.topology_panel, tr('Топология ЭП'))
    self.result_tabs.setTabVisible(self.topology_tab, False)
    self.nci_panel = NciPanel()
    self.nci_tab = self.result_tabs.addTab(self.nci_panel, tr('NCI'))
    self.result_tabs.setTabVisible(self.nci_tab, False)
    # the tabs under three common ones (a group with one tab shown is that tab)
    for title, tabs in ((tr('Результат'), (0, self.convergence_tab, self.thermo_tab, self.measured_tab)),
                        (tr('Спектры'), (self.vibrations_tab, self.uv_tab, self.nmr_tab)),
                        (tr('Волновая функция'), (self.field_tab, self.dos_tab, self.deloc_tab, self.topology_tab,
                                                  self.nci_tab))):
        for index in tabs:
            self.result_tabs.set_group(index, title)
    self.refresh_result_tools()  # the tools of the group of the page shown
    self.assessment = label(
        tr(
            'Нормальное завершение, сходимость оптимизации и проверка частот — разные условия. Здесь они рассматриваются отдельно.'
        ),
        'subtitle',  # plain lines under the status, not a box (the foot took too much room)
    )
    # the status and the assessment on the pill over the foot of the panel, no rows under it
    self.assessment.setWordWrap(True)
    status.addWidget(self.assessment)
    # a message of the window while the status is
    # on its pill — a line of the pill under a thin rule (status_note), not a second pill above it
    self.status_message = QLabel()
    self.status_message.setObjectName('statusMessage')
    self.status_message.setWordWrap(True)
    self.status_message.hide()
    status.addWidget(self.status_message)
    self.status_message_timer = QTimer(self)
    self.status_message_timer.setSingleShot(True)
    self.status_message_timer.timeout.connect(self.drop_status_note)
    self.status_timer.timeout.connect(self.drop_status_note)
    for item in (self.status_pill, self.calc_pulse):
        item.setParent(self.result_panel)
        item.raise_()
    self.status_pill.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
    self._status_place = _PlaceStatus(self)
    self.result_panel.installEventFilter(self._status_place)
    self.calc_pulse.installEventFilter(self._status_place)  # placed when it comes (a calculation started)
    # every tab of the result with the same margins inside its frame (some started at the very edge,
    # others had a card of their own)
    for i in range(self.result_tabs.count()):
        inner = self.result_tabs.widget(i).layout()
        if inner is not None:
            inner.setContentsMargins(*TAB_MARGINS)
    # the tabs whose page had no card of its
    # own get the frame of one — rounded, outlined, with the margins of a card
    for panel in (self.uv_panel, self.nmr_panel, self.convergence_panel, self.field_panel, self.topology_panel,
                  self.nci_panel):
        framed(panel)
    # the state of an empty tab at once — Quill instead of the table of the frequencies, no status lines
    # (it was set before the page of the frequencies existed: the empty table, Quill and the status were all shown)
    self.show_empty_quill(True)
    # the page of the results of a molecule, or of a
    # project of a crystal (modules/spectrum/views/crystal_view.py, built when first shown)
    from PySide6.QtWidgets import QStackedWidget

    self.results_stack = QStackedWidget()
    self.results_stack.addWidget(page)
    self.crystal_results = None
    self.stack.addWidget(self.results_stack)


class _PlaceStatus(QObject):
    """The pill of the status (and the spectrum of a running calculation) follow the size of the panel."""

    def __init__(self, owner):
        super().__init__()
        self.owner = owner

    def eventFilter(self, obj, event):
        try:
            if event.type() in (QEvent.Type.Resize, QEvent.Type.Show) and (event.type() == QEvent.Type.Resize
                                                                         or obj is not self.owner.result_panel):
                self.owner.place_status()
        except RuntimeError:
            pass
        return False
