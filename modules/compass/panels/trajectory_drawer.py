"""Optimization steps in Compass: a drawer over the left edge of the model field.

The drawer lists the cycles of a geometry optimization read from an ORCA output (energy relative to
the first cycle, in kcal/mol), with a small energy plot and playback. Compass shows the chosen cycle
in its own field (read-only) and marks the starting geometry — from the echo of the input file at
the top of the output, else the first cycle — with faint atoms joined by dashed lines. «Взять эту
геометрию» makes the cycle the structure of Compass. The keyboard moves through the cycles (see
Studio.trajectory_key).

The same drawer shows the points of a potential energy surface scan (the value of the
scanned coordinate, energy relative to the lowest point) and the steps of an IRC path (energy
relative to the transition state, marked TS) — load(steps, source, scan) with an orca_scan.Scan.

The drawer has four pages under a row of tabs (instead of the panel «Электронная плотность» on the right):
«Оптимизация» (the steps above), «Частоты» (load_modes(modes, base): the vibrations of the result, the chosen one
moves on the model — modeFrame(geometry) once per MODE_MS, one period a second, amplitude of the atom that moves
most), «Орбитали» and «QTAIM» (orbitals_host / aim_host, filled by modules/compass/panels/density_drawer.DensityDrawer).
page() / set_page(name) / pageChanged(name); best_page() — the first page with something in it.

A fifth page «Конформеры» (load_conformers(rows, source): (Molecule, energy | None, ΔE kcal/mol | None, share |
None) per conformer, the lowest first) — its tab is shown only once a search has found conformers; the chosen one is on
the model (conformerChanged(row)), «Взять этот конформер» (conformerAdoptRequested). With the tab the drawer is
WIDE px wide, so five tabs fit.
«Поверхности» is a page of its own between «Орбитали» and «QTAIM» (surfaces_host); the model moves right by
half the width of the drawer while it is open (viewer.set_inset, modules/compass/actions/trajectory_actions.py).
The pages are chosen in a drop-down list (PageChooser, under the name tab_bar) that offers only the pages with
something in them; the drawer is WIDTH wide again.
"""

from PySide6.QtCore import QEasingCurve, QPoint, QPropertyAnimation, QTimer, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QDoubleSpinBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QComboBox,
    QStackedWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)
from azimuth.icons import iconify
from azimuth.i18n import tr
from azimuth import quill
from modules.spectrum.views.trajectory import EnergyPlot

HARTREE_KCAL = 627.509474  # kcal/mol per hartree (CODATA 2018)


def delta_header(symbol='ΔE'):
    """«ΔE, ккал/моль» in the energy unit of «Настройки → Единицы»."""
    from azimuth import defaults

    return tr(symbol) + ', ' + tr(defaults.energy_name())


def conformer_delta(kcal):
    """ΔE of a conformer (the search gives kcal/mol) in the energy unit of «Настройки»."""
    from azimuth import defaults

    return '—' if kcal is None else f'{kcal / HARTREE_KCAL * defaults.energy_factor():.2f}'
WIDTH = 372  # four pages (was 296); a list of the pages, not tabs — the width of before
WIDE = 468  # with the tab «Конформеры»
EXTRA_TAB = 96  # the drawer grows by this much for each extra tab shown («Конформеры»)
PAGES = ('steps', 'modes', 'orbitals', 'surfaces', 'aim', 'conformers')  # no «Структуры» — the list of the project
DENSITY_PAGES = ('orbitals', 'surfaces', 'aim')  # the pages of the orbitals of the result
MODE_MS = 40  # a frame of the vibration on the model
SLIDE_MS = 320  # was 220 — as the sidebar of the Hub (hub/window.SLIDE_MS); the model moves in step (viewer.INSET_MS)


class PageChooser(QComboBox):
    """The pages of the drawer as a drop-down list — the interface of the QTabBar it replaced (addTab,
    setTabEnabled / isTabEnabled, setTabVisible / isTabVisible, setTabToolTip, tabText, currentIndex / setCurrentIndex,
    currentChanged with the number of the page). The list holds the pages that are visible, enabled and have something
    in them (has_content(index)); the page shown stays in it while it is shown."""

    currentChanged = Signal(int)

    def __init__(self, has_content=None, parent=None):
        super().__init__(parent)
        self.setObjectName('drawerPages')
        self.has_content = has_content or (lambda index: True)
        self._titles, self._enabled, self._visible, self._tips = [], [], [], []
        self._current = 0
        super().currentIndexChanged.connect(self._chosen)

    def addTab(self, title):
        self._titles.append(title)
        self._enabled.append(True)
        self._visible.append(True)
        self._tips.append('')
        self.refresh()
        return len(self._titles) - 1

    def count(self):
        return len(self._titles)

    def tabText(self, index):
        return self._titles[index]

    def setTabEnabled(self, index, on):
        self._enabled[index] = bool(on)
        self.refresh()

    def isTabEnabled(self, index):
        return self._enabled[index]

    def setTabVisible(self, index, on):
        self._visible[index] = bool(on)
        self.refresh()

    def isTabVisible(self, index):
        return self._visible[index]

    def setTabToolTip(self, index, text):
        self._tips[index] = text

    def offered(self, index):
        return self._visible[index] and self._enabled[index] and bool(self.has_content(index))

    def offered_pages(self):
        return [k for k in range(len(self._titles)) if self.offered(k)]

    def refresh(self):
        shown = [k for k in range(len(self._titles)) if self.offered(k) or k == self._current]
        self.blockSignals(True)
        self.clear()
        for k in shown:
            self.addItem(self._titles[k], k)
        row = self.findData(self._current)
        super().setCurrentIndex(row if row >= 0 else -1)
        self.blockSignals(False)

    def currentIndex(self):
        return self._current

    def setCurrentIndex(self, index):
        if index == self._current:
            return
        self._current = index
        self.refresh()
        self.currentChanged.emit(index)

    def _chosen(self, row):
        index = self.itemData(row)
        if index is not None and index != self._current:
            self._current = index
            self.currentChanged.emit(index)


class DrawerShadow(QWidget):
    """The soft shadow on the right of the drawer, a widget of its own next to it. It was a
    QGraphicsDropShadowEffect on the drawer — and with that effect the drawer stopped being painted on the screen after
    its pages were built anew (the QTAIM of Spectrum handed to Compass, seen by the user ☰ pressed, the
    model moved aside, no drawer; a grab of it showed it whole — a picture of it slid out on closing)."""

    WIDTH = 14

    def __init__(self, parent):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.hide()

    def paintEvent(self, event):
        from PySide6.QtGui import QColor, QLinearGradient, QPainter

        p = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), 0)
        gradient.setColorAt(0.0, QColor(20, 30, 50, 46))
        gradient.setColorAt(1.0, QColor(20, 30, 50, 0))
        p.fillRect(self.rect(), gradient)


class TrajectoryDrawer(QFrame):
    stepChanged = Signal(int)
    adoptRequested = Signal()
    openRequested = Signal()
    closeRequested = Signal()
    initialToggled = Signal(bool)
    pageChanged = Signal(str)  # 'steps', 'modes', 'orbitals', 'aim'
    modeFrame = Signal(object)  # the geometry of the vibration to show (None: the vibrations are left)
    conformerChanged = Signal(int)
    conformerAdoptRequested = Signal()
    spectrumRequested = Signal(str)  # the page shown — Spectrum opens the matching tab of the result
    mapRequested = Signal()  # the map of a two-dimensional scan

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName('trajectoryDrawer')
        self.steps = ()
        self.scan = None
        self.current = -1
        self._advancing = False
        self.source = ''
        self.folder = None
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.advance)
        self.conformers = ()  # [(Molecule, energy, ΔE, share)]
        self.conformer_current = -1
        self.conformer_source = ''
        self.modes = ()
        self.modes_base = None
        self.mode_current = -1
        self.mode_vectors = ()
        self.phase = 0.0
        self.mode_timer = QTimer(self)
        self.mode_timer.setInterval(MODE_MS)
        self.mode_timer.timeout.connect(self._mode_tick)
        self.setFixedWidth(WIDTH)
        # drawn like the cards of the program — the card title, a thin rule, a shadow, a table without frame
        # the shadow is a widget next to the drawer (DrawerShadow), not a graphics effect on it
        self.shadow = DrawerShadow(parent) if parent is not None else None
        column = QVBoxLayout(self)
        column.setContentsMargins(16, 14, 14, 14)
        column.setSpacing(9)
        head = QHBoxLayout()
        head.setSpacing(2)
        self.title = QLabel(tr('Шаги оптимизации'))
        self.title.setObjectName('cardtitle')
        head.addWidget(self.title, 1)
        # the folder of the calculation shown (it was «Открыть результат ORCA (.out)» — a window to choose
        # another result, named after one program of the eight read here)
        self.open_button = iconify(QPushButton(), 'folder', tr('Открыть папку расчёта'))
        # on every page — to Spectrum, to the tab of the result with the same thing (the user's wish)
        self.spectrum_button = iconify(QPushButton(), 'spectrum', tr('Перейти в Спектр'))
        self.close_button = iconify(QPushButton(), 'close', tr('Закрыть панель'))
        for b in (self.spectrum_button, self.open_button, self.close_button):
            b.setFixedSize(28, 28)
            head.addWidget(b)
        column.addLayout(head)
        # the result of the tab in pages — the steps, the vibrations, the orbitals and the density, QTAIM
        # a drop-down list of the pages instead of the row of tabs (the user's wish), only those with something
        # in them; the drawer keeps its width
        self.tab_bar = PageChooser(self._has_content)
        for title in (tr('Оптимизация'), tr('Частоты'), tr('Орбитали'), tr('Поверхности'), tr('QTAIM'), tr('Конформеры')):
            self.tab_bar.addTab(title)
        column.addWidget(self.tab_bar)
        rule = QFrame()
        rule.setObjectName('drawerRule')
        rule.setFixedHeight(1)
        column.addWidget(rule)
        self.pages = QStackedWidget()
        column.addWidget(self.pages, 1)
        steps_page = QWidget()
        steps = QVBoxLayout(steps_page)
        steps.setContentsMargins(0, 0, 0, 0)
        steps.setSpacing(9)
        self.pages.addWidget(steps_page)
        self.source_label = QLabel()
        self.source_label.setObjectName('subtitle')
        self.source_label.setWordWrap(True)
        steps.addWidget(self.source_label)
        self.message = QLabel(tr('Откройте выходной файл ORCA с оптимизацией геометрии.'))
        self.message.setObjectName('subtitle')
        self.message.setWordWrap(True)
        steps.addWidget(self.message)
        self.plot = EnergyPlot()
        self.plot.setMinimumSize(200, 110)
        self.plot.setFixedHeight(120)
        steps.addWidget(self.plot)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([tr('Цикл'), delta_header()])
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        self.table.setShowGrid(False)
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setAlternatingRowColors(True)
        steps.addWidget(self.table, 1)
        nav = QHBoxLayout()
        nav.setSpacing(4)
        self.previous = iconify(QPushButton(), 'step-prev', tr('Предыдущий шаг · ↑ или ←'))
        self.play = iconify(QPushButton(), 'play', tr('Проиграть шаги · пробел'))
        self.play.setCheckable(True)
        self.next = iconify(QPushButton(), 'step-next', tr('Следующий шаг · ↓ или →'))
        # a two-dimensional scan — its map (scan_map_view.ScanMapDialog)
        self.map_button = iconify(QPushButton(), 'scan-map', tr('Карта скана · энергия по двум координатам'))
        # the energy along the steps as a plot for a report: axes with units, the data as CSV
        self.profile_button = iconify(QPushButton(), 'spectrum', tr('Профиль энергии · график с осями и таблица для отчёта'))
        for b in (self.previous, self.play, self.next, self.map_button, self.profile_button):
            nav.addWidget(b)
        nav.addStretch(1)
        # an icon toggle like the other buttons of the row (was a check box with text)
        self.initial = iconify(
            QPushButton(),
            'initial-geometry',
            tr('Начальная геометрия · положения ядер в начале оптимизации: бледные атомы, связи пунктиром'),
        )
        self.initial.setCheckable(True)
        self.initial.setChecked(True)
        nav.addWidget(self.initial)
        steps.addLayout(nav)
        self.detail = QLabel()
        self.detail.setObjectName('subtitle')
        self.detail.setWordWrap(True)
        steps.addWidget(self.detail)
        self.adopt = QPushButton(tr('Взять эту геометрию'))
        self.adopt.setObjectName('primary')
        self.adopt.setToolTip(tr('Сделать выбранный шаг структурой Компаса и редактировать её'))
        steps.addWidget(self.adopt)
        self.pages.addWidget(self._modes_page())
        self.orbitals_host, self.orbitals_message = self._host_page(tr('В результате этой вкладки нет орбиталей.'))
        self.surfaces_host, self.surfaces_message = self._host_page(tr('В результате этой вкладки нет орбиталей.'))
        self.aim_host, self.aim_message = self._host_page(tr('QTAIM считается по орбиталям результата — в этой вкладке их нет.'))
        self.pages.addWidget(self._conformers_page())
        from azimuth.ui import StatusEcho

        # the messages of the orbitals and QTAIM pages (DensityPanel.status); told over the model for a while, not a
        # line here
        self.density_status = StatusEcho()
        self.density_status.setObjectName('subtitle')
        column.addWidget(self.density_status)
        self.steps_title = tr('Шаги оптимизации')
        self.tab_bar.currentChanged.connect(self._page_changed)
        self.previous.clicked.connect(lambda: self.select(self.current - 1))
        self.next.clicked.connect(lambda: self.select(self.current + 1))
        self.play.toggled.connect(self.set_playing)
        self.table.currentCellChanged.connect(lambda row, *_: self.show_step(row))
        self.plot.selected.connect(self.select)
        self.adopt.clicked.connect(self.adoptRequested)
        self.map_button.clicked.connect(self.mapRequested)
        self.profile_button.clicked.connect(lambda: self.show_profile())
        self.open_button.clicked.connect(self.openRequested)
        self.close_button.clicked.connect(self.closeRequested)
        self.spectrum_button.clicked.connect(lambda: self.spectrumRequested.emit(self.page()))
        self.initial.toggled.connect(self.initialToggled)
        self.slide = QPropertyAnimation(self, b'pos', self)
        self.slide.setDuration(SLIDE_MS)
        self.slide.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.slide.finished.connect(self._settle)
        self.load((), '')
        self.load_modes((), None)
        self.load_conformers((), '')
        self.hide()

    # -- content --------------------------------------------------------------------------------
    @property
    def geometry_of_step(self):
        return self.steps[self.current].geometry if 0 <= self.current < len(self.steps) else None

    def columns(self):
        """Headers and the reference energy of the table: optimization, scan or IRC."""
        scan = self.scan
        if scan is None:
            energies = [s.energy for s in self.steps if s.energy is not None]
            return tr('Шаги оптимизации'), [tr('Цикл'), delta_header()], energies[0] if energies else None
        ref = self.steps[scan.reference].energy if self.steps else None
        if scan.kind == 'irc':
            return tr('Путь IRC'), [tr('Шаг'), delta_header('ΔE от TS')], ref
        title = tr('Скан ППЭ · релаксированный') if scan.kind == 'relaxed' else tr('Скан ППЭ · жёсткий')
        names = [c.label + (', ' + c.unit if c.unit else '') for c in scan.coordinates]
        return title, [tr('Точка'), *names, delta_header()], ref

    def cells(self, i, step, ref):
        from azimuth import defaults

        delta = '—' if step.energy is None or ref is None else f'{(step.energy - ref) * defaults.energy_factor():+.2f}'
        if self.scan is None:
            return [str(step.cycle), delta]
        point = self.scan.points[i]
        if self.scan.kind == 'irc':
            return [str(point.number) + (' · TS' if point.ts else ''), delta]
        return [str(point.number), *(f'{v:.3f}' for v in point.values), delta]

    def load(self, steps, source='', scan=None):
        self.set_playing(False)
        self.steps = tuple(steps)
        self.tab_bar.refresh()
        self.scan = scan if scan is not None and len(scan.points) == len(self.steps) else None
        self.current = -1
        self.source = source
        self.folder = None  # the folder of a run whose steps have no file of the tab (a crystal)
        self.plot.steps = self.steps
        self.plot.current = -1
        title, headers, ref = self.columns()
        self.steps_title = title
        if self.page() == 'steps':
            self.title.setText(title)
        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(self.steps))
        for i, s in enumerate(self.steps):
            for j, value in enumerate(self.cells(i, s, ref)):
                item = QTableWidgetItem(value)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if s.energy is not None:
                    item.setToolTip(tr(f'E = {s.energy:.10f} хартри'))
                if s.geometry is None:
                    item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                self.table.setItem(i, j, item)
        self.table.blockSignals(False)
        has = bool(self.steps)
        self.source_label.setText(source)
        self.source_label.setVisible(bool(source))
        self.message.setVisible(not has)
        if has and self.scan is not None and self.scan.kind == 'irc' and all(s.geometry is None for s in self.steps):
            self.message.setText(
                tr(
                    'Геометрии пути IRC ORCA пишет в файл *_IRC_Full_trj.xyz рядом с выводом — он не найден; откройте его в Компасе («Файл → Открыть»).'
                )
            )
            self.message.setVisible(True)
        if source and not has:
            self.message.setText(tr('В этом файле нет явных циклов оптимизации геометрии.'))
        elif not has:
            self.message.setText(tr('Откройте выходной файл ORCA с оптимизацией геометрии.'))
        for w in (self.plot, self.table, self.previous, self.play, self.next, self.initial, self.detail, self.adopt):
            w.setVisible(has)
        self.play.setEnabled(len(self.steps) > 1)
        self.map_button.setVisible(self.is_map())
        self.profile_button.setVisible(len([s for s in self.steps if s.energy is not None]) > 1)
        if has:
            # an optimization opens on its last step with a geometry (the result); a scan or a path on the first
            last = next((i for i in range(len(self.steps) - 1, -1, -1) if self.steps[i].geometry is not None), 0)
            self.select(last if self.scan is None else 0)
        else:
            self.show_step(-1)
        self.plot.update()

    def profile_data(self):
        """(title, the label of x, the label of y, [(x, ΔE in the unit of the settings)]) of the energy along the steps:
        an optimization — by its cycles from the first; an IRC — by its steps from the transition state; a scan of one
        coordinate — by the value of the coordinate from the reference point. None without two energies."""
        from azimuth import defaults

        title, headers, ref = self.columns()
        points = []
        for i, step in enumerate(self.steps):
            if step.energy is None or ref is None:
                continue
            x = float(step.cycle) if self.scan is None else float(self.scan.points[i].number)
            if self.scan is not None and self.scan.kind != 'irc' and len(self.scan.coordinates) == 1:
                x = float(self.scan.points[i].values[0])
            points.append((x, (step.energy - ref) * defaults.energy_factor()))
        if len(points) < 2:
            return None
        return title, headers[0] if len(headers) == 2 else headers[1], headers[-1], points

    def show_profile(self):
        """The window of the energy profile (qe_plots.CurvesPlot in a QePlotWindow: «Сохранить данные…» — CSV)."""
        from modules.compass.actions import qe_plots

        found = self.profile_data()
        if found is None:
            return None
        title, x_label, y_label, points = found
        plot = qe_plots.CurvesPlot()
        plot.x_axis, plot.y_axis = x_label, y_label
        plot.series.append(('', '#2a62b8', points, points))
        window = qe_plots.QePlotWindow(self.window(), title, plot, [(x, e) for x, e in points], ['x', 'dE'], 'energy_profile.csv')
        window.header = [x_label.replace(',', ''), y_label.replace(',', '')]  # one column each in the CSV
        window.note.setText(tr('Энергия относительно: {}.').format(
            tr('первого шага') if self.scan is None else tr('переходного состояния') if self.scan.kind == 'irc'
            else tr('опорной точки скана')))
        self.profile_window = window
        window.show()
        return window

    def is_map(self):
        """The steps are a relaxed or rigid scan of two coordinates."""
        return bool(self.steps) and self.scan is not None and self.scan.kind != 'irc' and len(self.scan.coordinates) == 2

    def relabel_energies(self):
        """The unit of «Настройки → Единицы» changed — ΔE of the steps and the conformers rewritten in it."""
        _, headers, ref = self.columns()
        self.table.setHorizontalHeaderLabels(headers)
        last = len(headers) - 1
        for i, s in enumerate(self.steps):
            item = self.table.item(i, last)
            if item is not None:
                item.setText(self.cells(i, s, ref)[last])
        self.conformers_table.setHorizontalHeaderLabels([tr('Конформер'), delta_header(), tr('Доля, %')])
        for k, (_, _, delta, _) in enumerate(self.conformers):
            item = self.conformers_table.item(k, 1)
            if item is not None:
                item.setText(conformer_delta(delta))
        return headers

    def select(self, row):
        if 0 <= row < len(self.steps):
            self.table.setCurrentCell(row, 0)
            if self.current != row:
                self.show_step(row)

    def show_step(self, row):
        if not self._advancing:
            self.set_playing(False)
        self.current = row
        self.plot.current = row
        self.plot.update()
        self.previous.setEnabled(row > 0)
        self.next.setEnabled(0 <= row < len(self.steps) - 1)
        self.adopt.setEnabled(self.geometry_of_step is not None)
        if 0 <= row < len(self.steps):
            s = self.steps[row]
            energy = tr(f'{s.energy:.10f} хартри') if s.energy is not None else tr('нет однозначных данных')
            missing = '' if s.geometry else tr(' · Геометрия отсутствует или неполна')
            if self.scan is None:
                self.detail.setText(tr(f'Цикл {s.cycle} · E: {energy}') + missing)
            elif self.scan.kind == 'irc':
                point = self.scan.points[row]
                self.detail.setText(tr(f'Шаг {point.number} · E: {energy}') + (' · TS' if point.ts else '') + missing)
            else:
                point = self.scan.points[row]
                values = ', '.join(
                    f'{c.label} = {v:.3f}' + (' ' + c.unit if c.unit else '')
                    for c, v in zip(self.scan.coordinates, point.values)
                )
                note = tr(' · оптимизация точки не сошлась') if point.converged is False else ''
                self.detail.setText(tr(f'Точка {point.number} · ') + values + tr(f' · E: {energy}') + note + missing)
        else:
            self.detail.clear()
        self.stepChanged.emit(row)

    def set_shift(self, text):
        base = self.detail.text().split('\n')[0]
        self.detail.setText(base + ('\n' + text if text else ''))

    # -- pages -------------------------------------------------------------------------
    def _host_page(self, empty):
        """A page that the density panel fills (DensityDrawer.orbitals_page / aim_page); the message without orbitals."""
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(8)
        message = quill.EmptyNote(empty, 'no-orbitals')  # Quill with the empty frame of an orbital over the text
        column.addWidget(message)
        column.addStretch(1)
        self.pages.addWidget(page)
        return column, message

    def _modes_page(self):
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(9)
        # Quill with the empty frame — the result has no frequencies
        self.modes_message = quill.EmptyNote(tr('В результате этой вкладки нет частот. Откройте расчёт частот (Freq).'),
                                             'no-orbitals')
        column.addWidget(self.modes_message)
        self.modes_table = QTableWidget(0, 3)
        self.modes_table.setHorizontalHeaderLabels([tr('Мода'), tr('ν, см⁻¹'), tr('ИК, км/моль')])
        self.modes_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.modes_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.modes_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.modes_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.modes_table.verticalHeader().hide()
        self.modes_table.setShowGrid(False)
        self.modes_table.setFrameShape(QFrame.Shape.NoFrame)
        self.modes_table.setAlternatingRowColors(True)
        self.modes_table.currentCellChanged.connect(lambda row, *_: self.select_mode(row) if row != self.mode_current else None)
        column.addWidget(self.modes_table, 1)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.mode_play = iconify(QPushButton(), 'play', tr('Проиграть колебание на модели · пробел'))
        self.mode_play.setCheckable(True)
        self.mode_play.toggled.connect(self.set_mode_playing)
        row.addWidget(self.mode_play)
        row.addStretch(1)
        self.mode_amplitude_label = QLabel(tr('Амплитуда'))
        row.addWidget(self.mode_amplitude_label)
        self.mode_amplitude = QDoubleSpinBox()
        self.mode_amplitude.setRange(0.05, 1.0)
        self.mode_amplitude.setSingleStep(0.05)
        self.mode_amplitude.setValue(0.35)
        self.mode_amplitude.setSuffix(' Å')
        self.mode_amplitude.setToolTip(tr('Наибольшее смещение атома в анимации'))
        self.mode_amplitude.valueChanged.connect(lambda *_: self._emit_mode())
        row.addWidget(self.mode_amplitude)
        column.addLayout(row)
        self.mode_detail = QLabel()
        self.mode_detail.setObjectName('subtitle')
        self.mode_detail.setWordWrap(True)
        column.addWidget(self.mode_detail)
        self.mode_controls = (self.modes_table, self.mode_play, self.mode_amplitude_label, self.mode_amplitude, self.mode_detail)
        return page

    def page(self):
        index = self.tab_bar.currentIndex()
        return PAGES[index] if 0 <= index < len(PAGES) else 'steps'

    def set_page(self, name):
        index = PAGES.index(name) if name in PAGES else 0
        if self.tab_bar.currentIndex() == index:
            self._page_changed(index)
        else:
            self.tab_bar.setCurrentIndex(index)
        return self.page()

    def _page_changed(self, index):
        self.pages.setCurrentIndex(index)
        name = PAGES[index] if 0 <= index < len(PAGES) else 'steps'
        if name != 'steps':
            self.set_playing(False)
        if name != 'modes':
            self.set_mode_playing(False)
        titles = {'steps': self.steps_title, 'modes': tr('Колебания'), 'orbitals': tr('Электронная плотность'),
                  'surfaces': tr('Электронная плотность'), 'aim': tr('Электронная плотность'), 'conformers': tr('Конформеры')}
        self.title.setText(titles[name])
        self.density_status.setVisible(name in DENSITY_PAGES and bool(self.density_status.text()))
        self.pageChanged.emit(name)

    def best_page(self, orbitals=False):
        """The first page with something in it: steps, then vibrations, then orbitals."""
        if self.steps:
            return 'steps'
        if self.modes:
            return 'modes'
        return 'orbitals' if orbitals else 'steps'

    # -- conformers ----------------------------------------------------------------------
    def _conformers_page(self):
        page = QWidget()
        column = QVBoxLayout(page)
        column.setContentsMargins(0, 0, 0, 0)
        column.setSpacing(9)
        self.conformer_source_label = QLabel()
        self.conformer_source_label.setObjectName('subtitle')
        self.conformer_source_label.setWordWrap(True)
        column.addWidget(self.conformer_source_label)
        self.conformers_table = QTableWidget(0, 3)
        self.conformers_table.setHorizontalHeaderLabels([tr('Конформер'), delta_header(), tr('Доля, %')])
        self.conformers_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.conformers_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.conformers_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.conformers_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.conformers_table.verticalHeader().hide()
        self.conformers_table.setShowGrid(False)
        self.conformers_table.setFrameShape(QFrame.Shape.NoFrame)
        self.conformers_table.setAlternatingRowColors(True)
        self.conformers_table.currentCellChanged.connect(
            lambda row, *_: self.select_conformer(row) if row != self.conformer_current else None)
        column.addWidget(self.conformers_table, 1)
        self.conformer_detail = QLabel()
        self.conformer_detail.setObjectName('subtitle')
        self.conformer_detail.setWordWrap(True)
        column.addWidget(self.conformer_detail)
        self.conformer_adopt = QPushButton(tr('Взять этот конформер'))
        self.conformer_adopt.setObjectName('primary')
        self.conformer_adopt.setToolTip(tr('Сделать выбранный конформер структурой Компаса и редактировать её'))
        self.conformer_adopt.clicked.connect(self.conformerAdoptRequested)
        column.addWidget(self.conformer_adopt)
        return page

    def load_conformers(self, rows, source=''):
        """The conformers of the last search: (Molecule, energy | None, ΔE | None, share | None), the lowest first."""
        self.conformers = tuple(rows or ())
        self.conformer_source = source
        self.conformers_project = None  # set by the window when they are the conformers kept in a project
        self.conformer_current = -1
        table = self.conformers_table
        table.blockSignals(True)
        table.clearContents()
        table.setRowCount(len(self.conformers))
        for k, (molecule, energy, delta, share) in enumerate(self.conformers):
            cells = (str(k + 1), conformer_delta(delta), '—' if share is None else f'{100 * share:.1f}')
            for j, text in enumerate(cells):
                item = QTableWidgetItem(text)
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if energy is not None:
                    item.setToolTip(tr(f'E = {energy:.10f} хартри'))
                table.setItem(k, j, item)
        table.blockSignals(False)
        self.conformer_source_label.setText(source)
        self.conformer_source_label.setVisible(bool(source))
        has = bool(self.conformers)
        index = PAGES.index('conformers')
        self.tab_bar.setTabVisible(index, has)
        self.fit_width()
        if not has and self.page() == 'conformers':
            self.set_page('steps')
        self.conformer_adopt.setEnabled(False)
        self.conformer_detail.clear()
        if has:
            self.select_conformer(0)

    def fit_width(self):
        """Always WIDTH — the pages are a drop-down list (it grew by EXTRA_TAB for each extra tab)."""
        self.setFixedWidth(WIDTH)

    def _has_content(self, index):
        """A page is offered when it has something to show: the steps, the vibrations, the conformers, the
        structures; the pages of the orbitals when they are enabled (density_drawer.update_density_button)."""
        name = PAGES[index] if 0 <= index < len(PAGES) else ''
        if name == 'steps':
            return bool(getattr(self, 'steps', ()))
        if name == 'modes':
            return bool(getattr(self, 'modes', ()))
        if name == 'conformers':
            return bool(getattr(self, 'conformers', ()))
        return True

    @property
    def geometry_of_conformer(self):
        k = self.conformer_current
        return self.conformers[k][0] if 0 <= k < len(self.conformers) else None

    def select_conformer(self, row):
        if not 0 <= row < len(self.conformers):
            return
        self.conformer_current = row
        if self.conformers_table.currentRow() != row:
            self.conformers_table.blockSignals(True)
            self.conformers_table.setCurrentCell(row, 0)
            self.conformers_table.blockSignals(False)
        _, energy, delta, share = self.conformers[row]
        text = tr(f'Конформер {row + 1}')
        if energy is not None:
            text += tr(f' · E: {energy:.10f} хартри')
        self.conformer_detail.setText(text)
        self.conformer_adopt.setEnabled(True)
        self.conformerChanged.emit(row)

    # -- vibrations on the model ---------------------------------------------------------
    def load_modes(self, modes, base):
        self.set_mode_playing(False)
        self.modes = tuple(modes or ())
        self.tab_bar.refresh()
        self.modes_base = base
        self.mode_current = -1
        self.mode_vectors = ()
        self.phase = 0.0
        table = self.modes_table
        table.blockSignals(True)
        table.clearContents()
        table.setRowCount(len(self.modes))
        for i, m in enumerate(self.modes):
            freq = f'{abs(m.frequency):.2f}i' if m.frequency < 0 else f'{m.frequency:.2f}'
            for j, value in enumerate((m.index, freq, '—' if m.intensity is None else f'{m.intensity:.2f}')):
                item = QTableWidgetItem(str(value))
                item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                if m.frequency < 0:
                    item.setForeground(QColor('#d66a35'))
                    item.setToolTip(tr('Мнимая частота: анимация показывает направление неустойчивости.'))
                table.setItem(i, j, item)
        table.blockSignals(False)
        has = bool(self.modes)
        self.modes_message.setVisible(not has)
        for w in self.mode_controls:
            w.setVisible(has)
        if has:
            row = next((i for i, m in enumerate(self.modes) if m.animatable), 0)
            table.setCurrentCell(row, 0)
            self.select_mode(row)
        else:
            self.mode_detail.clear()

    def select_mode(self, row):
        from modules.spectrum.readers.vibration_data import normalized_vectors

        self.set_mode_playing(False)
        self.mode_current = row
        self.phase = 0.0
        mode = self.modes[row] if 0 <= row < len(self.modes) else None
        base = self.modes_base
        enabled = bool(mode is not None and mode.animatable and base is not None and len(mode.vectors) == len(base.atoms))
        self.mode_vectors = normalized_vectors(mode) if enabled else ()
        self.mode_play.setEnabled(enabled)
        self.mode_amplitude.setEnabled(enabled)
        if mode is not None:
            freq = f'{abs(mode.frequency):.2f}i' if mode.frequency < 0 else f'{mode.frequency:.2f}'
            text = tr(f'Мода {mode.index} · {freq} см⁻¹')
            if mode.frequency < 0:
                text += tr(' · мнимая: направление неустойчивости')
            if not enabled:
                text += ' · ' + tr('нет смещений атомов для анимации')
            self.mode_detail.setText(text)
        if enabled and self.page() == 'modes' and self.isVisible():
            self.set_mode_playing(True)
        else:
            self._emit_mode()

    def mode_geometry(self):
        from modules.spectrum.readers.vibration_data import displaced

        base = self.modes_base
        if base is None:
            return None
        if not self.mode_vectors:
            return base
        return displaced(base, self.mode_vectors, self.mode_amplitude.value(), self.phase)

    def _emit_mode(self):
        if self.page() == 'modes':
            self.modeFrame.emit(self.mode_geometry())

    def set_mode_playing(self, playing):
        playing = bool(playing and self.mode_play.isEnabled())
        self.mode_play.blockSignals(True)
        self.mode_play.setChecked(playing)
        self.mode_play.blockSignals(False)
        iconify(self.mode_play, 'pause' if playing else 'play',
                tr('Пауза · пробел') if playing else tr('Проиграть колебание на модели · пробел'))
        if playing:
            self.mode_timer.start()
        else:
            self.mode_timer.stop()
            self.phase = 0.0
            self._emit_mode()

    def toggle_mode_playing(self):
        self.set_mode_playing(not self.mode_timer.isActive())

    def _mode_tick(self):
        from math import pi

        self.phase = (self.phase + 2 * pi * MODE_MS / 1000.0) % (2 * pi)  # one period a second
        self._emit_mode()

    # -- playback (one printed cycle per tick, as in Spectrum) ----------------------
    def set_playing(self, playing):
        playing = bool(playing and len(self.steps) > 1)
        if playing and self.current >= len(self.steps) - 1:
            self.select(0)
        self.play.blockSignals(True)
        self.play.setChecked(playing)
        self.play.blockSignals(False)
        iconify(
            self.play,
            'pause' if playing else 'play',
            tr('Пауза · пробел') if playing else tr('Проиграть шаги · пробел'),
        )
        if playing:
            self.timer.start()
        else:
            self.timer.stop()

    def toggle_playing(self):
        self.set_playing(not self.timer.isActive())

    def advance(self):
        if not self.timer.isActive():
            return
        self._advancing = True
        try:
            if self.current < len(self.steps) - 1:
                self.select(self.current + 1)
            if self.current >= len(self.steps) - 1:
                self.set_playing(False)
        finally:
            self._advancing = False

    def reset_playback(self):
        self.set_playing(False)
        self.select(0)

    def hideEvent(self, event):
        self.set_playing(False)
        self.mode_timer.stop()
        super().hideEvent(event)
        if getattr(self, 'shadow', None) is not None:
            self.shadow.hide()

    def _follow_shadow(self):
        """The shadow stands right of the drawer, as tall, just under it in the stack."""
        shadow = getattr(self, 'shadow', None)
        if shadow is None:
            return
        g = self.geometry()
        shadow.setGeometry(g.right() + 1, g.top(), DrawerShadow.WIDTH, g.height())
        shadow.setVisible(self.isVisible())
        shadow.raise_()
        self.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        self._follow_shadow()

    def moveEvent(self, event):
        super().moveEvent(event)
        self._follow_shadow()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._follow_shadow()

    # -- sliding --------------------------------------------------------------------------------
    def place(self, rect):
        """Keep the drawer over the left edge of rect (the model field, in parent coordinates)."""
        self.setFixedHeight(rect.height())
        self._home = QPoint(rect.x(), rect.y())
        if self.slide.state() != QPropertyAnimation.State.Running:
            self.move(self._home)
        else:
            # the field moved while the drawer was sliding in (the first opening after a calculation hides
            # the editing row and the field goes up): the slide ends where the field is now, not where it was
            self.slide.setEndValue(self._home)
            start = self.slide.startValue()
            if isinstance(start, QPoint):
                self.slide.setStartValue(QPoint(start.x(), self._home.y()))

    def _settle(self):
        """After the slide the drawer stands exactly on the field, wherever the field is by then."""
        home = getattr(self, '_home', None)
        if home is not None and self.isVisible() and self.pos() != home:
            self.move(home)

    def open_drawer(self, animate=True):
        home = getattr(self, '_home', self.pos())
        leaving = getattr(self, '_leaving', None)
        self._leaving = None
        if leaving is not None:
            # closed and opened again at once (the list of the project made anew after a search) — the
            # picture leaving with its shadow goes now, and the drawer stands where it was, without sliding in again
            try:
                leaving.hide()
                leaving.deleteLater()
                animate = False
            except RuntimeError:  # it had left already
                pass
        if self.isVisible() and self.pos() == home and self.slide.state() != self.slide.State.Running:
            # open already — it stays, no slide again
            self._follow_shadow()
            return
        self.show()
        self.raise_()
        if animate and self.isVisible():
            self.slide.stop()
            self.slide.setEasingCurve(QEasingCurve.Type.OutCubic)
            self.slide.setStartValue(QPoint(home.x() - self.width(), home.y()))
            self.slide.setEndValue(home)
            self.slide.start()
        else:
            self.move(home)

    def close_drawer(self, animate=True):
        """It slides out as smoothly as it slides in. The drawer itself is hidden at once (the state is
        exact for the program); a picture of it travels to the left and disappears."""
        self.slide.stop()
        parent = self.parentWidget()
        if animate and self.isVisible() and parent is not None and self.width() > 0:
            # the picture leaves with its shadow (before, the shadow vanished at once and the picture sped up
            # to the end, InCubic); the model comes back with the same curve (viewer.set_inset)
            ghost = QWidget(parent)
            ghost.setObjectName('drawerGhost')
            ghost.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
            picture = QLabel(ghost)
            picture.setPixmap(self.grab())
            picture.setGeometry(0, 0, self.width(), self.height())
            shade = DrawerShadow(ghost)
            shade.setGeometry(self.width(), 0, DrawerShadow.WIDTH, self.height())
            shade.show()
            ghost.setGeometry(self.x(), self.y(), self.width() + DrawerShadow.WIDTH, self.height())
            ghost.show()
            ghost.raise_()
            away = QPropertyAnimation(ghost, b'pos', ghost)
            away.setDuration(SLIDE_MS)
            away.setEasingCurve(QEasingCurve.Type.InOutCubic)
            away.setStartValue(self.pos())
            away.setEndValue(QPoint(self.x() - self.width() - DrawerShadow.WIDTH, self.y()))
            away.finished.connect(ghost.deleteLater)
            away.start()
            self._leaving = ghost
        self.hide()
        # the shadow goes with the drawer even when the drawer was hidden already (no hideEvent then)
        if getattr(self, 'shadow', None) is not None:
            self.shadow.hide()
