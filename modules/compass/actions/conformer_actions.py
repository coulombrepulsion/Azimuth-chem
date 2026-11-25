"""Compass: «Правка → Поиск конформеров…» — candidates by turns, then GFN2-xTB energies.

§1 THEORY modules/compass/chemistry/conformers.py §1.
§2 ALGORITHM the window is a card «Метод поиска» — the method in a drop-down list (Перебор поворотов + xtb, Пчелиный
               поиск, CREST; the one suggested for the molecule by suggested_method), the settings of that method only,
               the energy window and the temperature of all; «Искать» runs it — and a card «Конформеры» with the table.
               The scan: «Найти» runs conformers.candidates on the structure (step 120°, 60° or 180°, at most N
               combinations, random beyond) and shows the distinct ones in a table and in the steps drawer (the steric
               score ranks them, no energy yet). «Уточнить в xtb» optimizes every candidate with xtb (--opt, GFN2-xTB,
               the charge, multiplicity and processes of Sextant) one after another in the folders of Sextant's runner;
               a timer polls the job; a failed run is skipped. Then conformers.cregen sorts them as CREST does (energy
               window 6 kcal/mol, duplicates ΔE < 0.05 kcal/mol and RMSD < 0.125 Å, rotamers by rotational constants
               within 1 %) and gives ΔE (kcal/mol), the number of rotamers and the Boltzmann shares at T (with that
               degeneracy); «Запустить CREST» runs CREST's own iMTD-GC search (crest molecule.xyz --gfn2 …,
               --quick on request) and reads crest_conformers.xyz; the drawer shows the optimized conformers, the lowest
               first, with their energies. «Взять выбранный» puts the chosen one into Compass (one undoable change);
               «Сохранить XYZ…» writes all of them as frames (the energy in the comment line).
§3 APPLICATIONS «Правка → Поиск конформеров…».
§4 SPECIFICATION ConformerWindow(owner): search() -> rows, refine() -> bool (started), poll() -> None | bool
               (finished), stop(), take(row), save_xyz(path=None), rows: [(Molecule, score, energy | None,
               ΔE | None, weight | None)].
§5 PROCEDURES below.
§6 NOTES xtb energies are electronic energies of GFN2-xTB in the gas phase (or the solvent chosen in
               Sextant); free energies need frequencies of each conformer.
§7 TESTS tests/test_gui.py::test_conformer_search_window.
§8' ROBUSTNESS no xtb: the button says where to set it; stopping keeps the conformers already optimized.
"""

from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from modules.compass.chemistry import conformers as cf
from azimuth.i18n import tr


class _Status(QLabel):
    """The line of the state of the search: shown only when it says something."""

    def __init__(self):
        super().__init__()
        self.setObjectName('subtitle')
        self.setWordWrap(True)
        self.hide()

    def setText(self, text):
        super().setText(text)
        self.setVisible(bool(text))


class ConformerWindow(QDialog):
    # the methods of the window — a choice in a drop-down list, each with its own settings
    METHODS = (
        ('scan', 'Перебор поворотов + xtb',
         'Повороты каждой вращаемой связи с шагом, отбор по стерике, затем оптимизация каждого кандидата в xtb '
         '(GFN2). Надёжно и предсказуемо, пока вращаемых связей немного (до 4–5).'),
        ('abc', 'Пчелиный поиск (ABC)',
         'Искусственная пчелиная колония по поворотам связей с энергиями GFN2-xTB: ищет низкие и непохожие друг на '
         'друга конформеры, не перебирая все сочетания. Для 5–10 вращаемых связей.'),
        ('crest', 'CREST (iMTD-GC)',
         'Метадинамика CREST с GFN2-xTB и сортировка CREGEN — самый полный поиск: находит и то, что не сводится к '
         'поворотам связей (кольца, водородные связи). Дольше всех.'),
    )
    SCAN_LIMIT = 200  # combinations of the scan by default (was 500): every one is an xtb optimization
    ABC_CONFORMERS = 10  # was 6 — with the energy window more conformers stay
    SMALL = 30  # atoms up to which CREST gets twice its metadynamics: it gives a small molecule only 5 ps

    def __init__(self, owner):
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QFormLayout, QStackedWidget, QWidget

        from azimuth.ui import button, card, center_combo, icon_button, label

        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(tr('Поиск конформеров'))
        self.setObjectName('workspace')  # the background and the cards of the program (as «Дополнительные настройки»)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.start = owner.coordinate_tool.table_molecule()
        self.rows = []
        self.queue = []
        self.results = []
        self.job = None
        self.timer = QTimer(self)
        self.timer.setInterval(500)
        self.timer.timeout.connect(self.poll)
        found = cf.rotors(self.start)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)
        body = QHBoxLayout()
        body.setSpacing(14)
        outer.addLayout(body, 1)

        # -- the card «Метод»: the choice and the settings of the method chosen
        frame, column = card(tr('Метод поиска'))
        frame.setFixedWidth(360)
        self.info = label(tr(f'Вращаемых связей: {len(found)} (без связей в циклах, CH₃ и амидных C–N).'), 'subtitle')
        column.addWidget(self.info)
        self.method = center_combo(QComboBox())
        for key, title, _ in self.METHODS:
            self.method.addItem(tr(title), key)
        from azimuth.ui import help_button

        # the methods are described behind a «?» button, not under the list
        self.method_note = help_button('\n\n'.join(f'{tr(title)} — {tr(text)}' for _, title, text in self.METHODS),
                                       tr('Методы поиска конформеров'))
        choice = QHBoxLayout()
        choice.setSpacing(8)
        choice.addWidget(self.method, 1)
        choice.addWidget(self.method_note, 0, Qt.AlignmentFlag.AlignVCenter)
        column.addLayout(choice)
        self.pages = QStackedWidget()
        column.addWidget(self.pages)

        def page():
            widget = QWidget()
            widget.setObjectName('conformerPage')
            widget.setStyleSheet('QWidget#conformerPage {background: transparent;}')
            form = QFormLayout(widget)
            form.setContentsMargins(0, 4, 0, 0)
            form.setSpacing(10)
            form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
            self.pages.addWidget(widget)
            return form

        scan = page()
        self.step = center_combo(QComboBox())
        for value in (120, 60, 180):
            self.step.addItem(f'{value}°', value)
        self.step.setToolTip(tr('120° — заторможенные положения связи sp³–sp³ (анти, гош±); 60° — и заслонённые'))
        scan.addRow(tr('Шаг поворота'), self.step)
        self.limit = QSpinBox()
        self.limit.setRange(1, 5000)
        self.limit.setValue(self.SCAN_LIMIT)
        self.limit.setToolTip(tr('Сочетаний больше — берётся столько случайных (исходная структура — всегда). '
                                 'Каждое — одна оптимизация в xtb'))
        scan.addRow(tr('Не больше сочетаний'), self.limit)
        self.refine_auto = QCheckBox(tr('Сразу уточнить в xtb (GFN2)'))
        self.refine_auto.setChecked(True)
        self.refine_auto.setToolTip(tr('Без галочки — только отбор по стерике, без энергий; уточнить можно потом'))
        scan.addRow(self.refine_auto)
        self.refine_button = button(tr('Уточнить в xtb (GFN2)'), self.refine)
        self.refine_button.setToolTip(tr('Оптимизировать каждый конформер в xtb и упорядочить по энергии'))
        self.refine_button.setMinimumHeight(self.refine_button.sizeHint().height())  # it was squeezed flat
        scan.addRow(self.refine_button)

        abc = page()
        self.abc_confs = QSpinBox()  # the bee colony (abc_search.py)
        self.abc_confs.setRange(2, 50)
        self.abc_confs.setValue(self.ABC_CONFORMERS)
        self.abc_confs.setToolTip(tr('Пчелиный поиск остановится, когда найдёт столько различных конформеров'))
        abc.addRow(tr('Конформеров'), self.abc_confs)
        self.abc_iterations = QSpinBox()
        self.abc_iterations.setRange(1, 100)
        self.abc_iterations.setValue(10)
        self.abc_iterations.setToolTip(tr('Итераций глобального поиска; у каждого следующего — вдвое меньше. Каждая '
                                          'итерация — 2 × (число вращаемых связей) коротких оптимизаций в xtb'))
        abc.addRow(tr('Итераций'), self.abc_iterations)

        crest = page()
        self.mdlen = QDoubleSpinBox()  # --mdlen x…
        self.mdlen.setRange(0.5, 5.0)
        self.mdlen.setDecimals(1)
        self.mdlen.setSingleStep(0.5)
        self.mdlen.setValue(2.0 if len(self.start.atoms) <= self.SMALL else 1.0)
        self.mdlen.setPrefix('× ')
        self.mdlen.setToolTip(tr('Длина метадинамики CREST относительно той, что он выбирает сам (--mdlen). Небольшие '
                                 'сопряжённые молекулы CREST считает жёсткими и даёт им всего 5 пс — длиннее находит больше'))
        crest.addRow(tr('Длина метадинамики'), self.mdlen)
        self.quick = QCheckBox(tr('Быстро (--quick)'))
        self.quick.setToolTip(tr('Сокращённый поиск CREST — для первого знакомства с молекулой'))
        crest.addRow(self.quick)

        # -- what every method shares
        common = QFormLayout()
        common.setSpacing(10)
        common.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.energy_window = QDoubleSpinBox()  # the energy window of all three
        self.energy_window.setRange(1.0, 30.0)
        self.energy_window.setDecimals(1)
        self.energy_window.setSingleStep(1.0)
        self.energy_window.setValue(cf.EWIN)
        self.energy_window.setSuffix(tr(' ккал/моль'))
        self.energy_window.setToolTip(tr('Конформеры выше самого низкого больше чем на столько не показываются (CREST: 6). '
                                  'Шире — видно и высокие формы, например anti-муравьиную кислоту (+7 ккал/моль)'))
        common.addRow(tr('Окно энергий'), self.energy_window)
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(10.0, 2000.0)
        self.temperature.setValue(298.15)
        self.temperature.setSuffix(' K')
        self.temperature.setToolTip(tr('Температура больцмановских долей'))
        common.addRow(tr('Температура для долей'), self.temperature)
        column.addSpacing(4)
        column.addWidget(label(tr('Для всех методов'), 'cardtitle'))
        column.addLayout(common)
        column.addStretch(1)
        self.go_button = button(tr('Искать'), self.start_search, True)
        self.go_button.setDefault(True)
        # one row under the list of conformers — the icons (their names under the pointer), «Искать»
        self.stop_button = icon_button(tr('Остановить поиск'), self.stop, 'stop')
        # the window put away, the search goes on; the
        # compass of the left panel (hub/job_indicator.py, azimuth/activities.py) shows it and opens it again
        self.away_button = icon_button(tr('Свернуть окно — поиск продолжится, компас в левой панели вернёт его'),
                                       self.put_away, 'hide')  # as «Скрыть» of the calculation
        self.away_button.setEnabled(False)
        # the card of the
        # method as tall as the settings of the method chosen, the window fixed to it (fit)
        self.method_card = frame
        body.addWidget(frame)
        # the names of 0.42–0.91 (tests and the busy state): one button starts any method now
        self.search_button = self.crest_button = self.abc_button = self.go_button

        # -- the card of the conformers found
        frame, column = card(tr('Конформеры'))
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([tr('№'), tr('Стерика'), tr('ΔE, ккал/моль'), tr('Ротамеров'), tr('Доля, %')])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # «ΔE…» whole
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.verticalHeader().hide()
        self.table.currentCellChanged.connect(lambda row, *_: self.show_row(row))
        column.addWidget(self.table, 1)
        self.status = _Status()  # no empty line under it
        # the compass of the program turns by the status while CREST, the bee search or xtb works (busy)
        from azimuth.controls import Spinner

        self.spinner = Spinner(18)
        status_row = QHBoxLayout()
        status_row.setSpacing(8)
        status_row.addWidget(self.spinner, 0, Qt.AlignmentFlag.AlignVCenter)
        status_row.addWidget(self.status, 1)
        column.addLayout(status_row)
        # the conformer chosen into Compass (✓), all of them into one XYZ file (the disk); no «Закрыть» — the window is
        # put away by its ✕ or «Свернуть»
        self.take_button = icon_button(tr('Взять выбранный конформер в Компас'), lambda: self.take(self.table.currentRow()),
                                       'check')
        self.save_button = icon_button(tr('Сохранить все конформеры одним файлом XYZ…'), lambda: self.save_xyz(), 'save')
        self.go_button.setToolTip(tr('Начать поиск выбранным методом с настройками слева'))
        # one row in the card of the conformers, under the table and its status
        run = QHBoxLayout()
        run.setSpacing(6)
        for item in (self.take_button, self.save_button):
            run.addWidget(item)
        run.addStretch(1)
        for item in (self.away_button, self.stop_button):
            run.addWidget(item)
        run.addWidget(self.go_button)
        column.addLayout(run)
        body.addWidget(frame, 1)
        for item in (self.refine_button, self.stop_button, self.take_button, self.save_button):
            item.setEnabled(False)
        self.method.currentIndexChanged.connect(self.method_changed)
        self.method.setCurrentIndex(max(0, self.method.findData(self.suggested_method(len(found)))))
        self.method_changed()
        self.fit()  # the window fixed to the settings of the method chosen (method_changed fits it again)

    @staticmethod
    def suggested_method(rotors):
        """The method a molecule starts with — the scan while it is small (3^4 = 81 combinations at 120°), the bee
        colony for 5–10 rotatable bonds, CREST beyond."""
        return 'scan' if rotors <= 4 else 'abc' if rotors <= 10 else 'crest'

    def method_changed(self, *args):
        key = self.method.currentData()
        index = next(k for k, (name, *_) in enumerate(self.METHODS) if name == key)
        self.pages.setCurrentIndex(index)
        if hasattr(self, 'method_card'):
            self.fit()
            # the page left gives its room back only when Qt has laid
            # the window out again — fitted once more after that
            QTimer.singleShot(0, self.fit)

    WIDTH = 950
    TABLE_HEIGHT = 220  # the least height of the table of conformers (they scroll in it)

    def fit(self):
        """The window as tall as the card of the method with the settings of the method chosen (the other
        pages of the settings take no room), its size fixed; the table of the conformers takes the rest and scrolls."""
        from PySide6.QtWidgets import QSizePolicy, QWidget

        # every widget is polished first (and again when shown): otherwise the sizes are read before the style sheet
        # gives the fields their height, and the fields of the method lie over one another
        self.ensurePolished()
        for widget in self.findChildren(QWidget):
            widget.ensurePolished()
        for k in range(self.pages.count()):
            page = self.pages.widget(k)
            policy = QSizePolicy.Policy.Preferred if k == self.pages.currentIndex() else QSizePolicy.Policy.Ignored
            page.setSizePolicy(policy, policy)
            page.adjustSize()
        current = self.pages.currentWidget()  # the stack as tall as the page shown — not the height Qt kept of another
        width = current.width() if current.width() > 50 else self.method_card.width() - 44
        tall = current.heightForWidth(width) if current.hasHeightForWidth() else -1
        self.pages.setFixedHeight(max(tall, current.sizeHint().height(), current.minimumSizeHint().height()))
        self.pages.updateGeometry()
        self.table.setMinimumHeight(self.TABLE_HEIGHT)
        layout = self.layout()
        self.setMinimumSize(0, 0)
        self.setMaximumSize(16777215, 16777215)
        layout.invalidate()
        layout.activate()
        try:
            height = layout.totalHeightForWidth(self.WIDTH) if layout.hasHeightForWidth() else -1
        except AttributeError:
            height = -1
        card = self.method_card  # the card of the method whole, its wrapped notes counted at its width
        need = card.heightForWidth(card.width()) if card.hasHeightForWidth() else -1
        need = max(need, card.sizeHint().height(), card.minimumSizeHint().height())
        margins = layout.contentsMargins()
        height = max(height, layout.totalSizeHint().height(), layout.totalMinimumSize().height(),
                     need + margins.top() + margins.bottom()) + 4
        self.setFixedSize(self.WIDTH, height)
        return height

    def project_place(self, document=None):
        """(the project, the molecule) of the tab searched — where its conformers go when it ends; the tab
        of a molecule drawn in no project yet (or in an empty project, not yet in it) gets its project first."""
        owner = self.owner
        if not hasattr(owner, 'document'):
            return None, ''
        document = document or owner.document()

        def place():
            path = getattr(document, 'research_project_path', '') or (
                owner.research_path() if document is owner.document() and hasattr(owner, 'research_path') else None)
            ident = getattr(document, 'research_molecule_id', '')
            return (path, ident) if path and ident else (None, '')

        found = place()
        if found[0] is None and document is owner.document():
            try:
                if hasattr(owner, 'research_path') and owner.research_path() and hasattr(owner, 'attach_project_placeholder'):
                    owner.attach_project_placeholder()  # the empty project of the tab: the molecule joins it
                elif hasattr(owner, 'keep_loose_molecule'):
                    owner.keep_loose_molecule()  # a molecule of no project: a draft «Новый проект» of its own
            except (OSError, ValueError, KeyError, AttributeError):
                pass
            found = place()
        return found

    def start_search(self):
        """«Искать» — the method chosen."""
        key = self.method.currentData()
        if key == 'crest':
            return self.run_crest()
        if key == 'abc':
            return self.run_abc()
        # with «Сразу уточнить в xtb» the candidates of the turns are not shown — neither
        # in the table nor in the drawer of Compass; only the result of xtb is, once
        refine_now = self.refine_auto.isChecked()
        rows = self.search(show=not refine_now)
        if rows and refine_now:
            return self.refine()
        return rows

    # -- the search ------------------------------------------------------------------------------------
    def search(self, show=True):
        """The candidates of the turns (steric score); show — into the table and the drawer (else only kept for xtb)."""
        try:
            found = cf.candidates(self.start, self.step.currentData(), self.limit.value())
        except ValueError as exc:
            exc.quill = 'nothing-found'  # Quill with the empty butterfly net
            self.owner.error(exc)
            return None
        self.rows = [(m, score, None, None, None, None) for m, score in found]
        if not show:
            self.table.setRowCount(0)
            self.status.setText(tr('Перебор: структур {} — уточняю в xtb…').format(len(self.rows)))
            return self.rows
        self.fill()
        self.to_drawer(tr('конформеры (стерика)'))
        self.status.setText(tr(f'Найдено различных конформеров: {len(self.rows)}. Энергий пока нет — «Уточнить в xtb».'))
        for item in (self.refine_button, self.take_button, self.save_button):
            item.setEnabled(bool(self.rows))
        return self.rows

    def fill(self):
        self.table.setRowCount(len(self.rows))
        for k, (m, score, energy, delta, weight, rotamers) in enumerate(self.rows):
            cells = (
                str(k + 1),
                '' if score is None else f'{score:.3f}',
                '' if delta is None else f'{delta:.2f}',
                '' if rotamers is None else str(rotamers),
                '' if weight is None else f'{100 * weight:.1f}',
            )
            for j, text in enumerate(cells):
                self.table.setItem(k, j, QTableWidgetItem(text))
        # «Стерика» is the score of a candidate of the turns
        # before xtb, the energies are of the structures after it — a column with nothing in any row is not shown
        for j in range(1, 5):
            empty = all(self.table.item(k, j) is None or not self.table.item(k, j).text()
                        for k in range(self.table.rowCount()))
            self.table.setColumnHidden(j, bool(self.rows) and empty)

    def to_drawer(self, source):
        owner = self.owner
        # the conformers have their own page «Конформеры» of the drawer (it appears after a search and keeps
        # them); the steps of an optimization stay on «Оптимизация»
        rows = tuple((replace(m, title=tr(f'Конформер {k + 1}')), energy, delta, weight)
                     for k, (m, _, energy, delta, weight, _) in enumerate(self.rows))
        owner.trajectory_tool.load_conformers(rows, source)
        if owner.stack.currentIndex() != 0:
            owner.navigate(0)
        owner.structure_tabs.setCurrentIndex(0)
        owner.trajectory_tool.set_trajectory_open(True, 'conformers')

    def show_row(self, row):
        drawer = getattr(self.owner, 'drawer', None)
        if drawer is not None and 0 <= row < len(drawer.conformers) and self.owner.browsing:
            drawer.select_conformer(row)

    # -- xtb ---------------------------------------------------------------------------------------------
    def refine(self):
        from modules.sextant import runner

        owner = self.owner
        program = runner.find_program('xtb', owner.run_tool.configured_program('xtb')) if hasattr(owner, 'run_tool') else None
        if program is None:
            owner.error(ValueError(tr('xtb не найдена: укажите её в Секстанте («Программа: xtb» → «Указать…»).')))
            return False
        self.program = program
        self.mode = 'xtb'
        self.queue = [m for m, *_ in self.rows]
        self.total = len(self.queue)
        self.results = []
        self.job = None
        self.busy(True)
        self.timer.start()
        self.next_job()
        return True

    ACTIVITY = 'conformers'  # its key on the board of the long work (azimuth/activities.py)

    def board(self):
        return getattr(self.owner, 'activities', None)

    def busy(self, on, end='done'):
        for item in (self.refine_button, self.go_button, self.method):
            item.setEnabled(not on)
        self.stop_button.setEnabled(on)
        self.away_button.setEnabled(on)
        board = self.board()
        if on:  # the compass turns while the search or the calculation goes on
            self.spinner.start()
            self.searched_document = getattr(self.owner, 'document', lambda: None)()  # the tab searched, whatever is shown
            if board is not None:
                board.start(self.ACTIVITY, tr('Поиск конформеров'), self.reopen, parked=not self.isVisible())
        else:
            self.spinner.stop()
            if board is not None:
                board.finish(self.ACTIVITY, end, note=self.status.text())

    def searching(self):
        return self.spinner.running()

    def put_away(self):
        """«Свернуть» — the window hidden, the search goes on; the compass of the left panel opens it."""
        board = self.board()
        if board is not None and self.searching():
            board.park(self.ACTIVITY, True)
        self.hide()
        if hasattr(self.owner, 'notify'):
            self.owner.notify(tr('Поиск конформеров идёт — компас в левой панели вернёт окно.'), 6000)
        return True

    def reopen(self):
        self.show()
        self.raise_()
        self.activateWindow()
        return self

    def showEvent(self, event):
        super().showEvent(event)
        if hasattr(self, 'method_card'):
            QTimer.singleShot(0, self.fit)  # the sizes as the program draws them, once it is on the screen
        board = self.board()
        if board is not None:
            board.park(self.ACTIVITY, False)

    def report(self):
        """The share done and the line of the status for the compass of the left panel."""
        board = self.board()
        if board is None or not self.searching():
            return None
        total = getattr(self, 'total', 0) or None
        done = len(getattr(self, 'results', ()) or ()) if getattr(self, 'mode', '') not in ('crest', 'abc') else None
        return board.progress(self.ACTIVITY, done=done, total=total if done is not None else None,
                              note=self.status.text())

    def run_crest(self):
        """CREST's own search on the structure; its ensemble is sorted again by cregen."""
        from modules.sextant import runner

        owner = self.owner
        program = runner.find_program('crest', owner.run_tool.configured_program('crest')) if hasattr(owner, 'run_tool') else None
        if program is None:
            owner.error(ValueError(tr('CREST не найдена (conda install -c conda-forge crest; рядом нужна и xtb).')))
            return False
        try:
            spec = runner.prepare('crest', program, self.start, self.calculation(), (), owner.run_tool.jobs_root(), quick=self.quick.isChecked(),
                                  crest={'ewin': self.energy_window.value(), 'mdlen': self.mdlen.value()})
            self.job = runner.Job(spec).start()
        except (ValueError, OSError) as exc:
            owner.error(exc)
            return False
        self.mode = 'crest'
        self.queue = []
        self.total = 1
        self.results = []
        self.busy(True)
        self.status.setText(tr('CREST ищет конформеры… (минуты — десятки минут)'))
        self.timer.start()
        return True

    def calculation(self):
        from azimuth.core import Calculation

        owner = self.owner
        get = lambda name, default: getattr(owner, name).value() if hasattr(owner, name) else default  # noqa: E731
        return Calculation(task='Оптимизация', charge=get('charge', 0), multiplicity=get('spin', 1), cores=get('cores', 1))

    def next_job(self):
        from modules.sextant import runner

        while self.queue:
            molecule = self.queue.pop(0)
            try:
                spec = runner.prepare('xtb', self.program, molecule, self.calculation(), (), self.owner.run_tool.jobs_root())
                self.job = runner.Job(spec).start()
                self.status.setText(tr(f'xtb: конформер {self.total - len(self.queue)} из {self.total}…'))
                return True
            except (ValueError, OSError) as exc:
                self.results.append((molecule, None))
                self.status.setText(str(exc))
        self.job = None
        self.finish()
        return False

    def poll(self):
        from modules.sextant import runner
        from modules.spectrum.readers.outputs import read_any

        if self.job is None:
            return None
        code = self.job.poll()
        if code is None:
            return None
        self.report()  # a step done — the ring of the left panel follows
        text = self.job.text()
        if getattr(self, 'mode', 'xtb') == 'crest':
            return self.finish_crest(code, text)
        if getattr(self, 'mode', 'xtb') == 'abc':
            return self.abc_step(code, text)
        energy, geometry = None, None
        if runner.finished_normally('xtb', text, code):
            try:
                out = read_any(text, str(self.job.spec.output))
                energy = out.energies[-1] if out.energies else None
                geometry = out.geometry
            except ValueError:
                pass
        self.results.append((geometry, energy))
        return self.next_job() is False

    # -- the bee colony ----------------------------------------------------------------------------
    def run_abc(self):
        """The search of abc_search.py: every structure it asks for is a short (or, for its best, a full) xtb
        optimization; the conformers it keeps go to the table and the drawer as the others do."""
        from datetime import datetime

        from modules.compass.chemistry import abc_search
        from modules.sextant import runner

        owner = self.owner
        program = runner.find_program('xtb', owner.run_tool.configured_program('xtb')) if hasattr(owner, 'run_tool') else None
        if program is None:
            owner.error(ValueError(tr('xtb не найдена: укажите её в Секстанте («Программа: xtb» → «Указать…»).')))
            return False
        iterations = self.abc_iterations.value()
        self.abc_progress = {}  # filled by the search — the stage, the local search and how many at most
        self.abc = abc_search.search(self.start, n_confs=self.abc_confs.value(), global_iterations=iterations,
                                     local_iterations=max(1, iterations // 2), temperature=self.temperature.value(),
                                     ewin=self.energy_window.value(), progress=self.abc_progress)
        try:
            request = next(self.abc)
        except ValueError as exc:
            self.abc = None
            owner.error(exc)
            return False
        self.program = program
        self.mode = 'abc'
        self.abc_count = 0
        self.abc_root = owner.run_tool.jobs_root() / datetime.now().strftime('ABC_%Y-%m-%d_%H-%M-%S')  # one folder for all runs
        self.results = []
        self.busy(True)
        self.timer.start()
        return self.abc_job(request)

    def abc_job(self, request):
        from modules.sextant import runner

        molecule, cycles = request
        calc = replace(self.calculation(), max_cycles=cycles or 200)
        while True:
            self.abc_short = bool(cycles)
            try:
                spec = runner.prepare('xtb', self.program, molecule, calc, (), self.abc_root)
                self.job = runner.Job(spec).start()
                self.abc_count += 1
                what = tr('короткая оптимизация') if cycles else tr('полная оптимизация лучшего')
                self.status.setText(self.abc_status(what))
                return True
            except (ValueError, OSError) as exc:
                self.status.setText(str(exc))
                try:
                    molecule, cycles = self.abc.send(None)
                except StopIteration as stop:
                    return self.abc_done(stop.value)
                except ValueError as failed:
                    return self.abc_failed(failed)
                calc = replace(self.calculation(), max_cycles=cycles or 200)

    def abc_status(self, what):
        """Where the bee colony is — «глобальный поиск» or «локальный поиск k из не больше N · найдено, отвергнуто»."""
        p = getattr(self, 'abc_progress', None) or {}
        if p.get('stage') == 'local':
            stage = tr(f'локальный поиск {p["local"]} из не больше {p["local_max"]} · найдено {p["taken"]}, '
                       f'отвергнуто {p["rejected"]}')
        else:
            stage = tr('глобальный поиск самого низкого')
        return tr(f'Пчелиный поиск: {stage} · xtb № {self.abc_count} ({what})…')

    @staticmethod
    def abc_answer(job, short):
        """(energy, Molecule) of an xtb optimization — a short one may stop before convergence: then the last step of
        xtbopt.log; None when there is nothing to take."""
        from modules.compass.chemistry.formats import read_xyz_frames
        from modules.sextant import runner
        from azimuth.core import read_xyz

        text = job.text()
        if not short and not runner.finished_normally('xtb', text, job.code):
            return None
        _, energy = runner.progress('xtb', text, job.spec.folder)
        geometry = None
        for name in ('xtbopt.log', 'xtbopt.xyz', 'xtblast.xyz'):
            path = job.spec.folder / name
            if not path.is_file():
                continue
            try:
                content = path.read_text(encoding='utf-8', errors='replace')
                geometry = read_xyz_frames(content)[-1] if name == 'xtbopt.log' else read_xyz(content)
                break
            except (ValueError, IndexError):
                continue
        if energy is None or geometry is None:
            return None
        return energy, geometry

    def abc_step(self, code, text):
        job, self.job = self.job, None
        if self.abc is None:
            return True
        if job.stopped:
            return True
        answer = self.abc_answer(job, self.abc_short)
        try:
            request = self.abc.send(answer)
        except StopIteration as stop:
            return self.abc_done(stop.value)
        except ValueError as exc:
            return self.abc_failed(exc)
        return self.abc_job(request) and False

    def abc_done(self, ensemble):
        self.abc = None
        self.results = list(ensemble or [])
        self.total = self.abc_count
        return self.finish(tr('конформеры (ABC)'))

    def abc_failed(self, exc):
        """The reason in a message, not only in the status line, with the charge and the multiplicity used."""
        self.abc = None
        self.timer.stop()
        self.busy(False, 'failed')
        calc = self.calculation()
        text = str(exc) + ' ' + tr(f'Сейчас: заряд {calc.charge}, 2S+1 = {calc.multiplicity} (меняются в Секстанте).')
        self.status.setText(text)
        failure = ValueError(text)
        failure.quill = 'nothing-found'  # the bee colony found nothing — Quill with the empty net
        self.owner.error(failure)
        return True

    def finish_crest(self, code, text):
        from modules.sextant import runner

        job, self.job = self.job, None
        self.timer.stop()
        ensemble = job.spec.folder / 'crest_conformers.xyz'
        if job.stopped or not runner.finished_normally('crest', text, code) or not ensemble.is_file():
            self.status.setText(self.crest_failure(text))
            self.busy(False, 'stopped' if job.stopped else 'failed')
            return True
        self.results = cf.read_ensemble(ensemble.read_text(encoding='utf-8', errors='replace'))
        self.total = len(self.results)
        self.crest_text = text  # the window of its CREGEN, for finish()
        return self.finish(tr('конформеры (CREST)'))

    def crest_failure(self, text):
        """Why CREST stopped, from its output (CREST 3.0.2: «Setting up backup calculator …ERROR
        STOP», «Initial geometry optimization failed!» for a radical C8H7N2O2)."""
        message = tr('CREST не закончил поиск: см. crest.out в папке расчёта.')
        if 'Initial geometry optimization failed' in text or 'ERROR STOP' in text:
            message = tr('CREST остановился на первой оптимизации структуры («Initial geometry optimization failed»).')
            if self.calculation().multiplicity > 1:
                message += ' ' + tr('Для этой открытой оболочки попробуйте пчелиный поиск или перебор с «Уточнить в xtb» — '
                                    'там считает сама xtb.')
            else:
                message += ' ' + tr('Проверьте структуру (связи, заряд) или попробуйте пчелиный поиск.')
        return message

    def finish(self, source=None):
        self.timer.stop()
        done = [(m, e) for m, e in self.results if m is not None and e is not None]
        sorted_ = cf.cregen(done, self.temperature.value(), ewin=self.energy_window.value())  # the window chosen
        self.rows = [(m, None, e, d, w, g) for m, e, d, w, g in sorted_]
        self.fill()
        if self.rows:
            # all those of the energy window, under the molecule searched.
            # Into the list of
            # the project first, then the drawer — opened before, it was closed at once by the list made anew
            path, ident = self.project_place(getattr(self, 'searched_document', None))
            if path and hasattr(self.owner, 'add_project_conformers'):
                self.owner.add_project_conformers(path, ident, [(m, e, d, w) for m, _, e, d, w, _ in self.rows])
            self.to_drawer(source or tr('конформеры (xtb)'))
        failed = len(self.results) - len(done)
        above, nearest = cf.above_window(done, self.energy_window.value())  # what the window left out, said
        crest_rigid = (getattr(self, 'mode', '') == 'crest' and len(self.rows) == 1 and cf.rotors(self.start))
        from modules.sextant import runner

        broken = getattr(self, 'mode', '') == 'crest' and runner.crest_window_broken(getattr(self, 'crest_text', ''))
        self.status.setText(
            tr(f'Структур {len(done)} из {self.total}; после сортировки CREGEN конформеров {len(self.rows)} '
               f'(окно {self.energy_window.value():g} ккал/моль).')
            + (tr(f' Выше окна: {above}, ближайшая на {nearest:.1f} ккал/моль выше — расширьте окно, чтобы увидеть её.')
               if above else '')
            + (tr(f' Не удалось: {failed}.') if failed else '')
            + (tr(' CREST нашёл один конформер, хотя вращаемые связи есть: он мог счесть молекулу жёсткой — '
                  'увеличьте длину метадинамики или попробуйте «Найти» и «Уточнить в xtb».') if crest_rigid and not broken
               else '')
            # CREST 3.0.2 on macOS sorted with a window of 0 — say so, not «the molecule is rigid»
            + (tr(' CREST 3.0.2 отбросил все конформеры, кроме самого низкого: на macOS его окно энергий всегда 0 '
                  '(ошибка CREST, crest-lab/crest#431). Переустановите CREST — «Расчёт → Установить программы для '
                  'расчёта…» ставит на Mac версию 2.12.') if broken else '')
        )
        self.busy(False)
        self.refine_button.setEnabled(False)
        for item in (self.take_button, self.save_button):
            item.setEnabled(bool(self.rows))
        return True

    def stop(self):
        self.queue = []
        if getattr(self, 'abc', None) is not None:  # the bee colony stops with the job
            self.abc.close()
            self.abc = None
            self.timer.stop()
            self.status.setText(tr('Пчелиный поиск остановлен.'))
            self.busy(False, 'stopped')
        if self.job is not None and self.job.running:
            self.job.stop()

    def closeEvent(self, event):
        if self.searching() and event.spontaneous():
            # the ✕ of the window
            # while it searches puts it away, the search goes on (the program's own close() — its end — stops it)
            event.ignore()
            self.put_away()
            return
        self.stop()
        super().closeEvent(event)


    # -- results ---------------------------------------------------------------------------------------
    def take(self, row):
        if not 0 <= row < len(self.rows):
            return False
        owner = self.owner
        if owner.browsing:
            owner.trajectory_tool.set_trajectory_open(False)
        molecule = replace(self.rows[row][0], title=self.start.title, bonds=self.start.bonds)
        owner.model_menu_tool.edit_structure(molecule, tr(f'Взят конформер {row + 1}.'))
        return True

    def save_xyz(self, path=None):
        if not self.rows:
            return None
        frames = []
        for k, (m, score, energy, delta, weight, rotamers) in enumerate(self.rows):
            lines = m.xyz().splitlines()
            lines[1] = f'conformer {k + 1}' + (f' E = {energy:.8f} Eh dE = {delta:.3f} kcal/mol p = {weight:.4f}' if energy is not None else f' steric {score:.4f}')
            frames.append('\n'.join(lines))
        text = '\n'.join(frames) + '\n'
        if path is None:
            return self.owner.save_text(tr('Сохранить конформеры'), 'XYZ (*.xyz)', text, 'conformers.xyz') or None
        from azimuth.files import atomic_write

        atomic_write(path, text)
        return Path(path)
