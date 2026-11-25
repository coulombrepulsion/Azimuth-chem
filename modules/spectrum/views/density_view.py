"""The window «Анализ электронной плотности» of the orbital window. Numbers: modules/spectrum/analysis/density.py.

HEADER two pages for the density of the orbitals open in the orbital window. «QTAIM»: the critical points of ρ found by
    Multiwfn in the file of these orbitals (nuclei, bonds, rings, cages), the detailed table (position, ρ, ∇²ρ, ε, G, V,
    H, |V|/G, the eigenvalues of the Hessian; the atoms of a bond from its bond path), the Poincaré–Hopf check; one
    button puts the points with the bond paths on the Compass model and takes them away, the row chosen pulses there.
    «Разность Δρ»: Δρ = ρ(molecule) − Σ ρ(fragments) (the fragments: orbital files computed at the same positions of
    their atoms; our own calculation — Multiwfn has no such item) on the Compass model or in the 3D window. The
    Laplacian and the other fields are Multiwfn's surfaces of Compass («Поверхности» of the drawer on the left); the
    maps in a plane and the profiles are «Карты и профили» of Spectrum (modules/spectrum/views/field_view.py) — the old
    slice of this window is gone. Wilkinson convention, sections 1-8 (theory and errors: density.py §1, §8).

    The same tools also live in the drawer on the left of Compass (modules/compass/panels/density_drawer.py) —
    DensityTools is shared; DensityPanel lays them out for a narrow column with the short list of the points (type,
    atoms, ρ, ∇²ρ, H); TopologyPanel is the tab «Топология ЭП» of Spectrum with the detailed table.
    A field or the critical points put on the Compass model from the window hand the work over to that panel
    (to_compass): the window hides, Compass shows the panel with the same orbitals.
§2 ALGORITHM Heavy work under a wait cursor and a cancellable progress dialog; results kept on the window.
§3 APPLICATIONS modules/spectrum/views/orbitals_view.py («Анализ ЭП…»), modules/compass/panels/density_drawer.py,
               modules/spectrum/workspace.py («Топология ЭП»).
§4 SPECIFICATION DensityTools (mixin): build_tools(layout) with .orbital_set, .source, .show_cube, .show_in_compass,
    .show_aim, .compact, .to_compass set by the class using it; .on_topology(topology), .clear_aim(), .aim_shown() — set
    by the host. .aim_page, .surfaces_page; compass_tab() -> 1 | 2. DensityPanel(orbital_set, source, show_in_compass,
    show_aim, parent=None): the narrow layout, always on the model. DensityDialog(orbital_set, source, show_cube=None,
    show_in_compass=None, show_aim=None, parent=None, to_compass=None): .add_fragment(orbital_set); .difference() ->
    (Cube, integral) | None; .find_points() -> Topology | None (by Multiwfn — set_multiwfn(source));
    .set_multiwfn(source); .points_on_model() -> bool; .toggle_points() -> bool; .sync_model_button(shown);
    .table_text() -> str. TopologyPanel(find, show_aim): .show_for(orbital_set, source, topology); .clear(). SHORT,
    DETAILED — the columns of the two tables (first «№»). point_labels(topology) -> {id(point): 'n1' | 'b1' | 'r1' |
    'c1' …}: the numbers of the tables and the model. TopologyPanel marks a row on the model on a double click
    (on_double; a click moves the mark without leaving Spectrum), its button of the model is the icon of Compass
    (iconic_model); the column «Тип» only for all the points. The column «Взаимодействие» of the detailed table names
    the interaction of every BCP (contacts.label; the criteria in its tooltip), the summary lists the hydrogen, halogen
    … bonds found by the geometry without a BCP, the CSV «<stem>_qtaim_contacts.csv» has all the contacts.
§7 TEST CASES tests/test_gui.py::test_electron_density_window, ::test_density_panel_in_compass.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
from PySide6.QtCore import QObject, Qt
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QListWidget,
    QPushButton,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.spectrum.analysis import contacts, density
from azimuth.i18n import tr
from azimuth import quill  # the messages with Quill

STEPS = ((0.25, 'Грубая сетка · 0,25 Å'), (0.15, 'Обычная сетка · 0,15 Å'), (0.10, 'Точная сетка · 0,10 Å'))
KIND_NAMES = {'bond': 'связь (3, −1)', 'ring': 'цикл (3, +1)', 'cage': 'клетка (3, +3)', 'nucleus': 'ядро (3, −3)'}
KIND_FILTERS = (  # which critical points the table and the model show
    ('all', 'Все точки'), ('nucleus', 'Ядра (3, −3)'), ('bond', 'Связи (3, −1)'), ('ring', 'Циклы (3, +1)'),
    ('cage', 'Клетки (3, +3)'),
)
KIND_SHORT = {'bond': 'связь', 'ring': 'цикл', 'cage': 'клетка', 'nucleus': 'ядро'}
SHORT = ('№', 'Тип', 'Атомы', 'ρ', '∇²ρ', 'H')  # the list of Compass; + the number of the point
# Spectrum; + «Взаимодействие»
DETAILED = ('№', 'Тип', 'Атомы', 'Взаимодействие', 'x, Å', 'y, Å', 'z, Å', 'ρ', '∇²ρ', 'ε', 'G', 'V', 'H', '|V|/G', 'λ1', 'λ2', 'λ3')
LETTERS = {'nucleus': 'n', 'bond': 'b', 'ring': 'r', 'cage': 'c'}  # the numbers of the points by kind
NEAREST = 0.6  # Å: a maximum without its nucleus named by Multiwfn belongs to the atom this close
ORBITAL_FILTER = 'Орбитали (*.molden *.input *.molf *.mold *.fchk *.fch *.out *.log);;Все файлы (*)'



class _Spread:
    """The columns of a table as wide as their contents, and the room left over the viewport shared equally among
    the visible ones — after every fill (spread()) and every resize of the table."""

    def __init__(self, table):
        from PySide6.QtCore import QEvent, QObject

        self.table = table
        spread = self.spread

        class Watch(QObject):
            def eventFilter(self, obj, event):
                if event.type() == QEvent.Type.Resize:
                    spread()
                return False

        self.watch = Watch(table)
        table.viewport().installEventFilter(self.watch)

    def spread(self):
        table = self.table
        table.resizeColumnsToContents()
        shown = [c for c in range(table.columnCount()) if not table.isColumnHidden(c)]
        if not shown:
            return
        room = table.viewport().width() - sum(table.columnWidth(c) for c in shown)
        if room > 0:
            extra, rest = divmod(room, len(shown))
            for k, c in enumerate(shown):
                table.setColumnWidth(c, table.columnWidth(c) + extra + (1 if k < rest else 0))


def point_labels(topology):
    """{id(point): 'n1' | 'b1' | 'r1' | 'c1' …} — every critical point numbered within its kind, in the order
    of the topology (the nuclei by atom, then bonds, rings, cages): the same numbers in the tables and on the model."""
    if topology is None:
        return {}
    counts, labels = {}, {}
    for point in list(getattr(topology, 'nuclei', ())) + list(topology.points):
        counts[point.kind] = counts.get(point.kind, 0) + 1
        labels[id(point)] = f'{LETTERS.get(point.kind, "?")}{counts[point.kind]}'
    return labels


class _Unmark(QObject):
    """A click on the row already chosen, a click on no row or Esc clears the choice of the table."""

    def __init__(self, table):
        super().__init__(table)
        self.table = table
        table.viewport().installEventFilter(self)
        table.installEventFilter(self)

    def eventFilter(self, watched, event):
        from PySide6.QtCore import QEvent, Qt

        kind = event.type()
        if kind not in (QEvent.Type.MouseButtonPress, QEvent.Type.KeyPress):
            return False  # the type first: the table is not touched while it is being deleted (an exception left
            # pending there came out of the next Python call of Qt as SystemError — the tests of the windows)
        try:
            table = self.table
            if (kind == QEvent.Type.MouseButtonPress and watched is table.viewport()
                    and event.button() == Qt.MouseButton.LeftButton):
                index = table.indexAt(event.position().toPoint())
                rows = table.selectionModel().selectedRows() if table.selectionModel() else []
                if not index.isValid() or (len(rows) == 1 and rows[0].row() == index.row()):
                    if rows:
                        table.clearSelection()
                        table.setCurrentItem(None)
                    return True
            if (kind == QEvent.Type.KeyPress and watched is table and event.key() == Qt.Key.Key_Escape
                    and table.selectionModel() and table.selectionModel().hasSelection()):
                table.clearSelection()
                return True
        except RuntimeError:
            pass
        return False


class DensityTools:
    """The pages «Δρ» and «QTAIM» and their work, for the window of Spectrum and for the Compass panel;
    the slice is gone (the maps are «Карты и профили» of Spectrum), the Laplacian and the other fields are
    Multiwfn's in the page «Поверхности» of Compass; the window and the tab «Топология ЭП» of Spectrum show the detailed
    table of the points, Compass — the short list (type, atoms, ρ, ∇²ρ, H)."""

    compact = False
    to_compass = None  # () -> None: hand the work over to the panel of Compass after a field is put on the model
    on_topology = None  # (topology) -> None — the points found, for the other views of the same orbitals
    clear_aim = None  # () -> None — take the points off the model
    aim_shown = None  # () -> bool — are points of the model there now
    keep_contacts = None  # (orbital_set, [(i, j, kind)]) -> bool — the weak interactions onto the model
    on_double = False  # a row marks its point on the model on a double click only (Spectrum: no jump on a click)
    iconic_model = False  # the button of the model is the icon of Compass (Spectrum)
    labels = {}

    def build_tools(self, layout):
        self.fragments = []
        self.topology = None
        self.tabs = QTabWidget()
        if self.compact:
            self.tabs.setDocumentMode(True)
        layout.addWidget(self.tabs, 1)
        from azimuth.ui import StatusEcho

        self.status = StatusEcho()  # the messages go to the status of the window, not a line of the page
        layout.addWidget(self.status)
        self.aim_page = self._aim_tab()
        self.surfaces_page = self._surfaces_tab()
        self.tabs.addTab(self.aim_page, tr('QTAIM'))
        self.tabs.addTab(self.surfaces_page, tr('Разность Δρ'))

    def compass_tab(self):
        """The tab of the drawer of Compass for the page shown (TAB_PAGES of modules/compass/panels/density_drawer.py)."""
        return 2 if self.tabs.currentWidget() is self.aim_page else 1

    def _text(self, text, short=''):
        """An explanation; in the narrow panel of Compass the short form, the whole text in its tooltip."""
        item = QLabel(short if self.compact and short else text)
        item.setWordWrap(True)
        if self.compact:
            item.setObjectName('subtitle')
            if short:
                item.setToolTip(text)
        return item

    @staticmethod
    def _style_table(table):
        """The tables drawn like the others of the program — no grid and no frame, rows striped, chosen whole."""
        from PySide6.QtWidgets import QFrame

        table.setShowGrid(False)
        table.setFrameShape(QFrame.Shape.NoFrame)
        table.setAlternatingRowColors(True)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.verticalHeader().hide()
        table.horizontalHeader().setHighlightSections(False)

    def _handed(self):
        if self.to_compass is not None:
            self.to_compass()

    # -- tabs ---------------------------------------------------------------------------------------------------
    def _surfaces_tab(self):
        """Δρ with the fragments (our own calculation: Multiwfn has no such item); the grid of the fields."""
        page = QWidget()
        column = QVBoxLayout(page)
        if self.compact:
            column.setContentsMargins(0, 6, 0, 0)
        row = QHBoxLayout()
        self.step = QComboBox()
        for value, title in STEPS:
            self.step.addItem(tr(title), value)
        self.step.setCurrentIndex(1)
        self.target = QComboBox(page)
        self.target.setVisible(not self.compact)
        if self.show_in_compass is not None:
            self.target.addItem(tr('на модели Компаса'), 'compass')
        if self.show_cube is not None:
            self.target.addItem(tr('в окне 3D'), 'window')
        if not self.compact:  # the panel of Compass shows the grid above its tabs and draws only on the model
            row.addWidget(self.step)
            row.addWidget(self.target)
            row.addStretch()
            column.addLayout(row)
            column.addWidget(self._text(tr('Лапласиан, ELF, LOL и другие поверхности — в Компасе: панель слева, вкладка '
                                           '«Поверхности».')))
        explanation = tr('Разность плотностей Δρ = ρ(молекула) − Σ ρ(фрагменты): как сдвинулись электроны при образовании '
                         'связей. Фрагменты — файлы орбиталей тех же атомов в тех же положениях (например, атомы или '
                         'две половины молекулы, посчитанные отдельно тем же методом и базисом).')
        if self.compact:  # a heading,
            # the three steps, buttons with icons (the words did not fit the narrow panel)
            head = QLabel(tr('Разность плотностей Δρ'))
            font = head.font()
            font.setBold(True)
            head.setFont(font)
            # the heading and «?» — the meaning and the three steps behind it, not lines of the page
            from azimuth.ui import help_button

            self.fragment_steps = help_button(
                explanation + '\n\n' + tr('Как посчитать: 1) посчитайте фрагменты отдельно — тем же методом и базисом, '
                                            'атомы на тех же местах; 2) «+» — добавьте файлы их орбиталей; 3) «Показать '
                                            'Δρ»: синее — электронов прибавилось, красное — убыло.'),
                tr('Разность плотностей Δρ'))
            heading = QHBoxLayout()
            heading.setSpacing(8)
            heading.addWidget(head, 0, Qt.AlignmentFlag.AlignVCenter)
            heading.addWidget(self.fragment_steps, 0, Qt.AlignmentFlag.AlignVCenter)
            heading.addStretch(1)
            column.addLayout(heading)
        else:
            column.addWidget(self._text(explanation, tr('Δρ: куда ушли электроны · нужны фрагменты')))
        self.fragment_list = QListWidget()
        self.fragment_list.setMaximumHeight(130)
        self.fragment_list.setToolTip(tr('Фрагменты Δρ: их сумма вычитается из плотности молекулы'))
        column.addWidget(self.fragment_list)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.add_fragment_button = add = QPushButton(tr('Добавить фрагмент…'))
        add.clicked.connect(self.choose_fragment)
        self.drop_fragment_button = drop = QPushButton(tr('Убрать фрагмент'))
        drop.clicked.connect(self.remove_fragment)
        self.difference_button = QPushButton(tr('Показать Δρ'))
        self.difference_button.clicked.connect(self.difference)
        if self.compact:
            from azimuth.icons import iconify

            iconify(add, 'plus', tr('Добавить фрагмент… · файлы орбиталей фрагментов (Molden, fchk, .gbw)'))
            iconify(drop, 'delete', tr('Убрать выбранный фрагмент'))
            self.difference_button.setToolTip(tr('Δρ на модели: синее — электронов прибавилось, красное — убыло'))
        for b in (add, drop, self.difference_button):
            row.addWidget(b)
        row.addStretch()
        column.addLayout(row)
        self.fragment_list.currentRowChanged.connect(lambda *a: self.update_fragment_buttons())
        self.update_fragment_buttons()
        column.addStretch()
        return page

    def _aim_tab(self):
        page = QWidget()
        column = QVBoxLayout(page)
        if self.compact:
            column.setContentsMargins(0, 6, 0, 0)
        about = tr('Критические точки плотности (теория «атомов в молекулах» Бейдера): точки связей и циклов, пути '
                   'связей. ∇²ρ < 0 и H < 0 в точке связи — общая (ковалентная) связь, ∇²ρ > 0 — замкнутые оболочки '
                   '(ионная связь, водородная, ван-дер-ваальсова); ε — эллиптичность: около 0 у одинарной связи, '
                   '0,2–0,3 у двойной. Всё в атомных единицах.')
        self.aim_help = None
        if self.compact:
            column.addWidget(self._text(about, tr('ρ, ∇²ρ и H в точках · подробная таблица — в Спектре, «Топология ЭП»')))
        else:  # the explanation in «?», the page keeps its room
            from azimuth.ui import help_button

            self.aim_help = help_button(about, tr('Что значат величины в критических точках'))
        row = QHBoxLayout()
        row.setSpacing(6)
        # the critical points are found by Multiwfn only (from the nuclei, all pairs, triangles and tetrahedra
        # of atoms) in the file of these orbitals; set_multiwfn gives the source, without it the button is off
        self.find_button = QPushButton(tr('Найти точки') if self.compact else tr('Найти критические точки'))
        self.find_button.setObjectName('primary')
        self.find_button.clicked.connect(self.find_points)
        self.multiwfn = None
        self.find_button.setEnabled(False)
        self.find_button.setToolTip(tr('Нужен файл этих орбиталей (Molden, fchk или .gbw ORCA)'))
        # one button puts the points on the model and takes them away
        self.model_button = QPushButton()
        if self.iconic_model:
            from azimuth.icons import iconify

            iconify(self.model_button, 'compass', tr('Перейти в Компас · критические точки на модели'))
        self.model_button.setCheckable(True)
        self.model_button.setEnabled(False)
        self.model_button.setVisible(self.show_aim is not None)
        self.model_button.clicked.connect(lambda: self.toggle_points())
        self.points_shown_on_model = False
        self.sync_model_button(False)
        from azimuth.icons import iconify

        copy = iconify(QPushButton(), 'copy', tr('Копировать таблицу'))  # an icon, like the other tools
        def copy_table():
            from azimuth.ui import copied

            QApplication.clipboard().setText(self.table_text())
            copied(self, tr('таблица критических точек'), copy)  # said

        copy.clicked.connect(copy_table)
        # the CSV tables of the points are written to «Анализ» when they are found — the folder at one click
        self.folder_button = iconify(QPushButton(), 'folder', tr('Папка с таблицами точек (CSV) — «Анализ» рядом с '
                                                                 'файлом орбиталей'))
        self.folder_button.clicked.connect(lambda: self.open_tables_folder())
        self.folder_button.setEnabled(False)
        for b in (self.find_button, self.model_button):
            row.addWidget(b)
        self.aim_row = row  # the drawer of Compass puts its turning ring here
        row.addStretch()
        row.addWidget(copy)
        row.addWidget(self.folder_button)
        # in the narrow drawer of Compass the folder is the one of its header
        self.folder_button.setVisible(not self.compact)
        if self.aim_help is not None:
            row.addWidget(self.aim_help)
        column.addLayout(row)
        # the kind of critical points shown — nuclei, bonds, rings, cages or all; a row chosen in the table is
        # marked on the model
        self.kind_filter = QComboBox()
        for key, title in KIND_FILTERS:
            self.kind_filter.addItem(tr(title), key)
        self.kind_filter.setToolTip(tr('Какие критические точки показать в таблице и на модели'))
        self.kind_filter.currentIndexChanged.connect(self.refresh_points)
        column.addWidget(self.kind_filter)
        # until the points are found — Quill with the flag at the middle of a bond (docs/art/QUAIL_ART_DIALOGS.md)
        self.points_note = quill.EmptyNote(tr('Критические точки ещё не найдены — нажмите «Найти точки».') if self.compact
                                           else tr('Критические точки ещё не найдены — нажмите «Найти критические точки».'),
                                           'no-points')
        column.addWidget(self.points_note)
        self.shown_points = []
        headers = DETAILED if not self.compact else SHORT
        self.table = QTableWidget(0, len(headers))
        self.table.setHorizontalHeaderLabels([tr(h) for h in headers])
        # every column as wide as its contents (the atoms stretched in Compass were squeezed to nothing by the
        # long numbers of the nuclei), the last one takes the rest
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        if self.compact:
            self.table.horizontalHeader().setStretchLastSection(True)
        else:  # the wide table of Spectrum — every column as wide as its contents, the room left shared by all
            # (the last one took it all; Stretch for all cut «ядро (3, −3)» and the big numbers of the nuclei)
            self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            self._spreader = _Spread(self.table)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self._style_table(self.table)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.itemSelectionChanged.connect(self.point_chosen)
        self.table.cellDoubleClicked.connect(lambda *_: self.point_opened())
        # the row chosen is let go by a second click on it, a click below the rows or Esc — the ring on the model goes
        # with it
        self._unmark = _Unmark(self.table)
        if self.on_double:
            self.table.setToolTip(tr('Двойной щелчок — точка на модели Компаса'))
        column.addWidget(self.table, 1)
        self.aim_summary = QLabel()
        self.aim_summary.setObjectName('subtitle')
        self.aim_summary.setWordWrap(True)
        column.addWidget(self.aim_summary)
        return page

    # -- work -----------------------------------------------------------------------------------------------------
    def _run(self, work, title=None, total=0):
        """Work(step) in a worker thread, the window painting meanwhile (azimuth.tasks.run_waiting);
        None after «Отмена» or an error (said in a message)."""
        from azimuth.tasks import run_spinning, run_waiting

        spinner = getattr(self, 'spinner', None)  # in the drawer of Compass — a ring, no waiting window
        try:
            # the search of the tab «Топология ЭП» runs
            # in the panel of the drawer of Compass, hidden then — its ring was not seen; the wait of the window instead
            place = spinner.parentWidget() if spinner is not None else None  # the ring itself is hidden until it turns
            if spinner is not None and place is not None and place.isVisible():
                return run_spinning(work, spinner, title or tr('Анализ плотности…'))
            return run_waiting(self, title or tr('Анализ плотности…'), work, total)
        except InterruptedError:
            return None
        except (ValueError, MemoryError, np.linalg.LinAlgError) as exc:
            quill.warning(self, tr('Анализ плотности'), str(exc))
            return None

    def _show(self, cube, kind, title):
        if self.target.currentData() == 'compass' and self.show_in_compass is not None:
            shown = self.show_in_compass(cube, kind, self.orbital_set, title)
            self._handed()  # the rest is done in the panel of Compass next to the model
            return shown
        if self.show_cube is not None:
            self.show_cube(cube, False)
            return True
        return False

    def handover_state(self):
        """What the panel of Compass takes over from the window: the fragments and the critical points."""
        names = [self.fragment_list.item(i).text() for i in range(self.fragment_list.count())]
        return {'fragments': list(zip(self.fragments, names)), 'topology': self.topology}

    def add_fragment(self, orbital_set, name=''):
        self.fragments.append(orbital_set)
        formula = orbital_set.molecule.formula
        self.fragment_list.addItem(f'{name or orbital_set.title or tr("фрагмент")} · {formula}')
        self.update_fragment_buttons()

    def update_fragment_buttons(self):
        """«Убрать фрагмент» with a fragment chosen, «Показать Δρ» with at least one; the count of the atoms
        of the fragments against the molecule in the tooltip of the list."""
        if not hasattr(self, 'difference_button'):
            return
        fragments = getattr(self, 'fragments', [])
        self.drop_fragment_button.setEnabled(0 <= self.fragment_list.currentRow() < len(fragments))
        self.difference_button.setEnabled(bool(fragments))
        if fragments:
            atoms = sum(len(f.molecule.atoms) for f in fragments)
            molecule = getattr(getattr(self, 'orbital_set', None), 'molecule', None)
            total = len(molecule.atoms) if molecule is not None else atoms
            self.fragment_list.setToolTip(tr(f'Атомов во фрагментах: {atoms} из {total}'))

    def choose_fragment(self):
        paths, _ = QFileDialog.getOpenFileNames(self, tr('Орбитали фрагментов'), str(Path.home()), tr(ORBITAL_FILTER))
        from modules.spectrum.readers.orbital_files import read_orbitals

        for path in paths:
            try:
                text = Path(path).read_text(encoding='utf-8-sig', errors='replace')
                self.add_fragment(read_orbitals(text), Path(path).name)
            except (OSError, ValueError) as exc:
                quill.warning(self, tr('Орбитали фрагмента не прочитаны'), f'{Path(path).name}: {exc}', 'file-unreadable')

    def remove_fragment(self):
        row = self.fragment_list.currentRow()
        if 0 <= row < len(self.fragments):
            del self.fragments[row]
            self.fragment_list.takeItem(row)
        self.update_fragment_buttons()

    def difference(self):
        if not self.fragments:
            quill.warning(self, tr('Разность плотностей'), tr('Добавьте фрагменты: «Добавить фрагмент…».'), 'nothing-found')
            return None
        grid, fragments = self.step.currentData(), tuple(self.fragments)  # a snapshot for the worker
        found = self._run(lambda step: density.difference_cube(self.orbital_set, list(fragments), grid, progress=step),
                          tr('Разность плотностей: орбитали…'), 1)
        if found is None:
            return None
        cube, integral = found
        expected = float(self.orbital_set.occupied()[1].sum() - sum(f.occupied()[1].sum() for f in self.fragments))
        self.status.setText(tr(f'∫Δρ dV = {integral:+.3f} e (ожидается {expected:+.3f} e — разница от шага сетки).'))
        self._show(cube, 'difference', tr('Разность плотностей Δρ'))
        return found

    def set_multiwfn(self, source):
        """Source() -> (program, wavefunction file, cores) or None — the file of these orbitals."""
        self.multiwfn = source
        self.find_button.setEnabled(source is not None)
        self.find_button.setToolTip(
            tr('Поиск от ядер, от всех пар, троек и четвёрок атомов: находит и связи, которых Компас не рисует, '
               'циклы и клетки') if source is not None
            else tr('Нужен файл этих орбиталей (Molden, fchk или .gbw ORCA)'))

    def find_points(self):
        """The critical points of Multiwfn in the file of these orbitals (set_multiwfn)."""
        return self.find_points_multiwfn()

    def find_points_multiwfn(self):
        from modules.spectrum.wavefunction import multiwfn

        source = getattr(self, 'multiwfn', None)
        given = source() if source is not None else None
        if not given:
            return None
        program, path, cores = given
        found = self._run(lambda step: multiwfn.run_topology(program, path, cores, step),
                          tr('Поиск критических точек…'), 0)
        if found is None:
            return None
        cps, text, number, warnings = found
        topology = self._run(lambda step: density.topology_from(cps, self.orbital_set, warnings), tr('Пути связей…'), 0)
        if topology is None:
            return None
        from modules.spectrum.wavefunction import field_tables

        written = []
        try:  # the output of Multiwfn and the tables of the points by their kinds, in «Анализ»
            base = Path(path)
            stem = base.name.split('.')[0]
            field_tables.save_output(base, 'topology', text)
            symbols = [a.symbol for a in self.orbital_set.molecule.atoms]
            tables = field_tables.cp_tables(topology, symbols)
            header, rows = contacts.table(self.find_contacts(topology), symbols)  # the weak interactions
            if rows:
                tables['qtaim_contacts'] = (header, rows)
            written = field_tables.write_tables(base.parent, stem, tables, family=field_tables.QTAIM_TABLES)
            field_tables.save_topology(base, topology)  # shown again when the result is opened again
        except OSError:
            pass
        if written:
            self.tables_folder = written[0].parent
        self.show_topology(topology)
        self.contacts_to_model()
        count = len(topology.points) + len(topology.nuclei)
        self.status.setText(tr(f'Найдено критических точек: {count}.') + (
            ' ' + tr('Таблицы — в папке «Анализ» расчёта.') if written else ''))
        return topology

    def show_topology(self, topology, tell=True):
        """The table and the summary of the critical points (also those found in the window); of the
        kind chosen (kind_filter), the nuclei too; tell — pass them to on_topology."""
        self.topology = topology
        self.weak = self.find_contacts(topology)
        self.contact_of = contacts.by_point(self.weak)
        if hasattr(self, 'folder_button'):
            self.folder_button.setEnabled(self.tables_place() is not None)
        self.labels = point_labels(topology)
        counts = {'all': len(topology.points) + len(getattr(topology, 'nuclei', ())), 'nucleus': len(getattr(topology, 'nuclei', ()))}
        for kind in ('bond', 'ring', 'cage'):
            counts[kind] = sum(p.kind == kind for p in topology.points)
        for k, (key, title) in enumerate(KIND_FILTERS):
            self.kind_filter.setItemText(k, tr(title) + f' · {counts[key]}')
        self.refresh_points()
        c = topology.counts
        lines = [tr(f'Ядер n = {c["n"]}, связей b = {c["b"]}, циклов r = {c["r"]}, клеток c = {c["c"]}: '
                    f'n − b + r − c = {topology.poincare_hopf}') + (' ✓' if topology.poincare_hopf == 1 else ' ⚠')]
        lines += ['⚠ ' + note for note in topology.notes]
        unseen = self.contacts_without_points()
        if unseen and not self.compact:  # an interaction without a BCP is still one (Lane et al. 2013)
            lines.append(tr(f'Без критической точки связи (по геометрии): {unseen}.'))
        self.aim_summary.setText('\n'.join(lines))
        self.model_button.setEnabled(self.show_aim is not None)
        if tell and self.on_topology is not None:
            self.on_topology(topology)
        return topology

    weak = ()  # the contacts of the topology shown (modules/spectrum/analysis/contacts.py)
    contact_of = {}

    def find_contacts(self, topology):
        """The weak interactions of the molecule of these orbitals named (modules/spectrum/analysis/contacts.py):
        every BCP and every close pair without one; the total charge from the nuclei and the occupied orbitals."""
        orbital_set = self.orbital_set
        if orbital_set is None or topology is None:
            return ()
        try:
            charge = round(sum(orbital_set.charges) - float(np.sum(orbital_set.occupied(False)[1])))
        except (AttributeError, TypeError, ValueError):
            charge = 0
        try:
            return contacts.classify(orbital_set.molecule, topology, charge)
        except (ValueError, IndexError):
            return ()

    def weak_pairs(self):
        """(i, j, kind) of the weak interactions with a BCP of the points shown here."""
        return [(c.atoms[0], c.atoms[1], c.kind) for c in self.weak if c.point is not None and c.kind != 'covalent']

    def contacts_to_model(self):
        """Right after a search its weak interactions are drawn on the model of Compass — when it shows the
        structure of these orbitals (keep_contacts); the points themselves still go there by the button."""
        if self.keep_contacts is None or self.orbital_set is None:
            return False
        try:
            return bool(self.keep_contacts(self.orbital_set, self.weak_pairs()))
        except (RuntimeError, AttributeError):
            return False

    def contacts_without_points(self):
        """The named interactions (not van der Waals) that have no BCP, for the summary."""
        symbols = [a.symbol for a in self.orbital_set.molecule.atoms] if self.orbital_set is not None else []
        found = [c for c in self.weak if c.point is None and c.kind in contacts.ORDER]
        return '; '.join(f'{contacts.label(c, symbols)} ({c.distance:.2f} Å, {c.angle:.0f}°)' for c in found)

    def chosen_points(self, key=None):
        """The points of the kind chosen: nuclei first, then bonds, rings, cages."""
        topology = self.topology
        if topology is None:
            return []
        key = key or self.kind_filter.currentData()
        everything = list(getattr(topology, 'nuclei', ())) + list(topology.points)
        return everything if key == 'all' else [p for p in everything if p.kind == key]

    def point_atoms(self, point):
        """The atoms of a point; a maximum whose nucleus Multiwfn did not name — the atom within NEAREST Å."""
        if point.atoms or point.kind != 'nucleus' or self.orbital_set is None:
            return point.atoms
        atoms = self.orbital_set.molecule.atoms
        if not atoms:
            return ()
        xyz = np.array([(a.x, a.y, a.z) for a in atoms], float)
        distance = np.linalg.norm(xyz - np.asarray(point.position, float), axis=1)
        k = int(np.argmin(distance))
        return (k,) if distance[k] < NEAREST else ()

    def cells(self, point, symbols):
        """The row of a point: the short one of Compass or the detailed one of Spectrum; first its
        number within the kind (n1, b2 …) — the label of the point on the model."""
        atoms = '–'.join(f'{symbols[k]}{k + 1}' for k in self.point_atoms(point) if 0 <= k < len(symbols))
        label = self.labels.get(id(point), '')
        if self.compact:
            return [label, tr(KIND_SHORT[point.kind]), atoms, f'{point.rho:.4f}', f'{point.laplacian:+.4f}',
                    f'{point.energy:+.4f}']
        ratio = abs(point.potential) / point.kinetic if point.kinetic > 1e-12 else float('nan')
        contact = self.contact_of.get(id(point))
        named = contacts.label(contact, symbols) if contact is not None else ''
        return [label, tr(KIND_NAMES[point.kind]), atoms, named, *(f'{c:.4f}' for c in point.position),
                f'{point.rho:.5f}', f'{point.laplacian:+.5f}',
                '' if point.ellipticity is None else f'{point.ellipticity:.3f}',
                f'{point.kinetic:.5f}', f'{point.potential:+.5f}', f'{point.energy:+.5f}', f'{ratio:.2f}',
                *(f'{v:+.4f}' for v in point.eigenvalues)]

    def refresh_points(self):
        self.shown_points = self.chosen_points()
        symbols = [a.symbol for a in self.orbital_set.molecule.atoms] if self.orbital_set is not None else []
        self.table.blockSignals(True)
        self.table.setRowCount(len(self.shown_points))
        for row, point in enumerate(self.shown_points):
            for column, value in enumerate(self.cells(point, symbols)):
                item = QTableWidgetItem(value)
                if column > 2 and (self.compact or column != 3):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                if column == 3 and not self.compact and id(point) in self.contact_of:  # the criteria
                    item.setToolTip(contacts.detail(self.contact_of[id(point)], symbols))
                self.table.setItem(row, column, item)
        self.table.blockSignals(False)
        # the column «Тип» only for all the points — a table of one kind says it in the list above
        self.table.setColumnHidden(1, self.kind_filter.currentData() != 'all')
        if getattr(self, '_spreader', None) is not None:
            self._spreader.spread()
        self.points_note.setVisible(getattr(self, 'topology', None) is None)
        if self.points_shown_on_model:  # from Spectrum the model follows without going there
            self.points_on_model(handed=False, go=not self.on_double)

    def chosen_row(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        return rows[0].row() if rows else None

    def point_chosen(self):
        """The row chosen is marked on the model (when the points are there); the mark pulses;
        in Spectrum (on_double) a click marks it there without going to Compass — the double click goes."""
        if self.points_shown_on_model:
            self.points_on_model(handed=False, go=not self.on_double)

    def point_opened(self):
        """A double click — the points on the model of Compass with this one marked (also when they were
        not there yet)."""
        if self.on_double and self.topology is not None and self.show_aim is not None:
            # only the points of
            # the kind of the one opened go to the model; the panel of Compass follows (show_aim → follow_kind)
            row = self.chosen_row()
            kind = self.shown_points[row].kind if row is not None and row < len(self.shown_points) else None
            return self.points_on_model(handed=False, kind=kind)
        return False

    def follow_kind(self, key):
        """The list of kinds shows key (the kind the model shows now) without sending the points again."""
        index = self.kind_filter.findData(key)
        if index < 0 or index == self.kind_filter.currentIndex():
            return False
        shown = self.points_shown_on_model
        self.points_shown_on_model = False  # the model is already as it should be
        self.kind_filter.blockSignals(True)
        self.kind_filter.setCurrentIndex(index)
        self.kind_filter.blockSignals(False)
        try:
            self.refresh_points()
        finally:
            self.points_shown_on_model = shown
        return True

    def sync_model_button(self, shown):
        """The button tells what it does next — put the points on the model or take them away."""
        self.points_shown_on_model = bool(shown)
        self.model_button.blockSignals(True)
        self.model_button.setChecked(self.points_shown_on_model)
        self.model_button.blockSignals(False)
        if self.iconic_model:  # the icon stays, the tooltip tells
            self.model_button.setToolTip(tr('Убрать критические точки с модели Компаса') if self.points_shown_on_model
                                         else tr('Перейти в Компас · критические точки на модели'))
        elif self.points_shown_on_model:
            self.model_button.setText(tr('Убрать с модели'))
            self.model_button.setToolTip(tr('Убрать критические точки с модели Компаса'))
        else:
            self.model_button.setText(tr('На модель') if self.compact else tr('Показать на модели Компаса'))
            self.model_button.setToolTip(tr('Показать критические точки на модели Компаса'))

    def toggle_points(self):
        """The points on the model, or off it when they are there."""
        there = self.points_shown_on_model and (self.aim_shown is None or self.aim_shown())
        if there:
            if self.clear_aim is not None:
                self.clear_aim()
            self.sync_model_button(False)
            return False
        return self.points_on_model()

    def points_on_model(self, handed=True, go=True, kind=None):
        """The points of the kind chosen on the model (bond paths with the bonds), the chosen row marked;
        go=False — the model changes, the window stays where it is (Spectrum); kind — of this kind only."""
        from dataclasses import replace as _replace

        if self.topology is None or self.show_aim is None:
            self.sync_model_button(False)
            return False
        key = kind or self.kind_filter.currentData()
        points = self.chosen_points(key)
        paths = self.topology.paths if key in ('all', 'bond') else ()
        row = self.chosen_row()
        selected = self.shown_points[row].position if row is not None and row < len(self.shown_points) else None
        shown_topology = _replace(self.topology, points=tuple(points), paths=tuple(paths))
        labels = [self.labels.get(id(p), '') for p in points]  # the numbers of the table next to the points
        try:
            extra = {} if go else {'go': False}
            # the weak interactions with a BCP, whatever kind of points is shown
            extra['contacts'] = self.weak_pairs()
            shown = bool(self.show_aim(shown_topology, self.orbital_set, self.source, selected=selected, labels=labels,
                                       **extra))
        except TypeError:  # a host without the mark or the numbers
            shown = bool(self.show_aim(shown_topology, self.orbital_set, self.source))
        self.sync_model_button(shown)
        if handed:
            self._handed()
        return shown

    tables_folder = None  # where the tables of the points were written («Анализ»)
    folder_source = None  # () -> Path | None: the folder of the result when the points were found elsewhere

    def tables_place(self):
        if self.tables_folder is not None and Path(self.tables_folder).is_dir():
            return Path(self.tables_folder)
        return self.folder_source() if self.folder_source is not None else None

    def open_tables_folder(self):
        from PySide6.QtCore import QUrl
        from PySide6.QtGui import QDesktopServices

        folder = self.tables_place()
        if folder is not None:
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))
        return folder

    def table_text(self):
        rows = ['\t'.join(self.table.horizontalHeaderItem(j).text() for j in range(self.table.columnCount()))]
        for i in range(self.table.rowCount()):
            rows.append('\t'.join(self.table.item(i, j).text() if self.table.item(i, j) else '' for j in range(self.table.columnCount())))
        return '\n'.join(rows + [self.aim_summary.text()])


class DensityDialog(DensityTools, QDialog):
    def __init__(self, orbital_set, source, show_cube=None, show_in_compass=None, show_aim=None, parent=None,
                 read=None, to_compass=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(tr('Азимут · Анализ электронной плотности · ') + source)
        self.resize(980, 640)
        self.orbital_set = orbital_set
        self.source = source
        self.show_cube = show_cube
        self.show_in_compass = show_in_compass
        self.show_aim = show_aim
        self.read = read
        self.to_compass = to_compass
        self.build_tools(QVBoxLayout(self))


class DensityPanel(DensityTools, QWidget):
    """The tools in the narrow panel of Compass: every field goes on the model."""

    compact = True

    def __init__(self, orbital_set, source, show_in_compass, show_aim, parent=None):
        super().__init__(parent)
        self.orbital_set = orbital_set
        self.source = source
        self.show_cube = None
        self.show_in_compass = show_in_compass
        self.show_aim = show_aim
        self.read = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.build_tools(layout)


class TopologyPanel(DensityTools, QWidget):
    """The tab «Топология ЭП» of Spectrum — the detailed table of the critical points of the result; find() runs
    the search (in the panel of Compass, so that both show the same points), show_for() gets the points found anywhere
    for the orbitals of the result. A double click on a row goes to Compass (a click only chooses it), the
    button of the model is the icon of Compass."""

    on_double = True
    iconic_model = True

    def __init__(self, find=None, show_aim=None, parent=None):
        super().__init__(parent)
        self.orbital_set = None
        self.source = ''
        self.show_cube = None
        self.show_in_compass = None
        self.show_aim = show_aim
        self.read = None
        self.finder = find
        self.fragments = []
        self.topology = None
        layout = QVBoxLayout(self)
        self.aim_page = self._aim_tab()
        layout.addWidget(self.aim_page, 1)
        from azimuth.ui import StatusEcho

        self.status = StatusEcho()  # the messages go to the status of the window, not a line of the page
        layout.addWidget(self.status)
        self.find_button.setEnabled(find is not None)
        self.find_button.setToolTip(tr('Поиск в Multiwfn по файлу орбиталей результата; точки — и на модели Компаса'))

    def find_points(self):
        if self.finder is None:
            return None
        return self.finder()

    def show_for(self, orbital_set, source, topology):
        self.orbital_set, self.source = orbital_set, source
        return self.show_topology(topology, tell=False)

    def clear(self):
        self.topology = None
        self.orbital_set = None
        self.weak, self.contact_of = (), {}
        self.shown_points = []
        self.labels = {}
        self.table.setRowCount(0)
        self.points_note.show()
        self.aim_summary.clear()
        self.status.clear()
        self.model_button.setEnabled(False)
        self.sync_model_button(False)
        for k, (key, title) in enumerate(KIND_FILTERS):
            self.kind_filter.setItemText(k, tr(title))
