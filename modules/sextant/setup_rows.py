"""Which fields of «Постановка задачи» of Sextant stand in the card and which are in «Дополнительные настройки…».

§1 PURPOSE
    The card shows the fields set most often and fits the window without a scroll bar (the owner, 2026-11-22: «убери
    прокрутку постановки задачи. Все должно влезать, остальное — в доп настройки. Снаружи только максимально частые и
    популярные … чтоб пользователь сам мог настраивать постановку задачи»). The rest moves into the section «Задача» of
    «Дополнительные настройки…»; the button «Поля…» at the foot of the card chooses which fields stand outside.
§2 RULES
    1. The program, the task (and the steps of a chain), the method and the basis set always stand in the card, as do
       the fields a task cannot do without (the coordinate and the end of a scan, the atoms of a fragment of CDA).
    2. Every other row is movable (MOVABLE); by default outside are the solvent, the resources, the switch of the
       transition state and the number of excited states (DEFAULT_OUTSIDE) — with the dispersion too a chain with
       TD-DFT was 3 px taller than the card of a window of 1133 × 730; the name of the calculation, the dispersion, the
       finer settings of a task, the second coordinate of a scan (a 2D scan is rare) and the charges
       and multiplicities of the fragments of CDA (the note under the task tells them) are inside.
    3. The choice is kept in the preferences (KEY: the keys outside, comma separated); an unknown key is ignored.
    4. A row keeps its place among the rows of its form (the order of the form), and its visibility (a program or a
       task without the field hides it) wherever it stands: show(widget, flag) is the only way the window hides one.
§4 SPECIFICATION
    KEY, MOVABLE, DEFAULT_OUTSIDE, FIXED, CRYSTAL_*; SetupRows(window, form, inside, rows, key=KEY, movable=MOVABLE,
    defaults=DEFAULT_OUTSIDE, titles=TITLES, store=window.preferences, after=None): rows — [(key, widget)] in the order
    of the card (several widgets may share a key: the rows of one program each); outside() -> set, set_outside(keys), toggle(key, flag), reset(), show(widget, flag),
    visible(widget) -> bool, label(widget) -> QLabel | None, form_of(widget), title(key), menu() -> QMenu.
    The page of a crystal (crystal_mode.py) does the same with CRYSTAL_*: the program, the task, the method, the basis
    set or the cutoffs, the grid of the density and the grid of k always stand in the card; by default outside are the
    dispersion, the resources and the supercell; the name, the cell (primitive) and the thresholds of a relaxation are
    inside. The panel (qe_window.QePanel.show_rows) hides the rows a program does not use in whichever form holds them.
§7 TESTS
    tests/gui/test_gui_files.py::test_the_fields_of_the_crystal_setup_move_into_the_dialog,
    tests/gui/test_gui_sextant.py::test_the_fields_of_the_setup_move_between_the_card_and_the_dialog,
    ::test_the_setup_fits_the_window_of_a_laptop_for_every_task.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QCheckBox, QMenu

from azimuth.i18n import tr

KEY = 'sextant_setup_outside'
FIXED = ('program', 'task', 'chain_steps', 'method', 'basis', 'task_box', 'scan_index', 'scan_end', 'cda_atoms',
         'task_note')
MOVABLE = ('calc_title', 'solvent', 'dispersion', 'resources', 'stability', 'ts', 'opt_conv', 'calc_hessian',
           'temperature', 'num_freq', 'raman', 'couplings', 'states', 'tddft_mode', 'triplets', 'nto', 'scan2_index',
           'scan2_end', 'cda_charge', 'cda_mult2')
DEFAULT_OUTSIDE = frozenset(('solvent', 'resources', 'ts', 'states'))
TITLES = {'calc_title': 'Название', 'solvent': 'Растворитель', 'dispersion': 'Дисперсия',
          'resources': 'Ресурсы (процессы и память)', 'opt_conv': 'Сходимость и предел циклов оптимизации',
          'temperature': 'Температура и давление', 'states': 'Число возбуждённых состояний',
          'tddft_mode': 'Приближение TD-DFT', 'scan2_index': 'Вторая координата скана',
          'scan2_end': 'Конец и точки второй координаты', 'cda_charge': 'Заряд и мультиплетность фрагмента 1 (CDA)',
          'cda_mult2': 'Мультиплетность фрагмента 2 (CDA)'}


# the page of a crystal (crystal_mode.py): Quantum ESPRESSO and CP2K
CRYSTAL_KEY = 'sextant_crystal_setup_outside'
CRYSTAL_MOVABLE = ('calc_title', 'vdw', 'resources', 'primitive', 'supercell', 'relax')
CRYSTAL_DEFAULT_OUTSIDE = frozenset(('vdw', 'resources', 'supercell'))
CRYSTAL_TITLES = {'calc_title': 'Название', 'vdw': 'Дисперсия', 'resources': 'Ресурсы (процессы и память)',
                  'primitive': 'Ячейка (примитивная или файла)', 'supercell': 'Суперячейка',
                  'relax': 'Пороги оптимизации'}


class SetupRows:
    def __init__(self, window, form, inside, rows, key=KEY, movable=MOVABLE, defaults=DEFAULT_OUTSIDE, titles=None,
                 store=None, after=None):
        self.w = window
        self.key, self.movable, self.defaults = key, tuple(movable), frozenset(defaults)
        self.titles = TITLES if titles is None else titles
        self.store = store if store is not None else getattr(window, 'preferences', None)
        self.after = after  # called when the choice changed (the heading of the task follows what stands outside)
        self.form = form  # the card
        self.inside = inside  # the form of the section «Задача» of the dialog
        self.rows = list(rows)
        self.labels = {}
        self.wanted = {}
        for key, widget in self.rows:  # the labels Qt made for the rows stay theirs
            label = form.labelForField(widget)
            self.labels[widget] = label
            # hidden only when hidden on purpose (setRowVisible): isRowVisible is False until the window is shown, and
            # a widget not yet shown is «hidden» too
            explicit = widget.testAttribute(Qt.WidgetAttribute.WA_WState_ExplicitShowHide)
            self.wanted[widget] = not (explicit and widget.isHidden())
        self.chosen = self.saved()
        self.place()

    # -- the choice ------------------------------------------------------------------------------------------------
    def saved(self):
        text = self.store.value(self.key, None) if self.store is not None else None
        if text is None:
            return set(self.defaults)
        if isinstance(text, (list, tuple)):  # QSettings may give a list for «a,b»
            text = ','.join(str(x) for x in text)
        return {k for k in str(text).split(',') if k in self.movable}

    def outside(self):
        return set(self.chosen)

    def set_outside(self, keys):
        self.chosen = {k for k in keys if k in self.movable}
        if self.store is not None:
            self.store.setValue(self.key, ','.join(k for k in self.movable if k in self.chosen) or '-')
        self.place()
        if self.after is not None:
            self.after()
        return self.outside()

    def toggle(self, key, flag):
        keys = self.outside()
        (keys.add if flag else keys.discard)(key)
        return self.set_outside(keys)

    def reset(self):
        return self.set_outside(self.defaults)

    def is_outside(self, key):
        return key not in self.movable or key in self.chosen

    # -- the rows --------------------------------------------------------------------------------------------------
    def form_of(self, widget):
        for form in (self.form, self.inside):
            if form.getWidgetPosition(widget)[0] >= 0:
                return form
        return None

    def place(self):
        """Take every row out and put it back, in the order of the card, into the card or the section «Задача»."""
        for key, widget in self.rows:
            form = self.form_of(widget)
            if form is not None:
                form.takeRow(widget)
        for key, widget in self.rows:
            target = self.form if self.is_outside(key) else self.inside
            label = self.labels.get(widget)
            if label is not None:
                target.addRow(label, widget)
            else:
                target.addRow(widget)
            self._apply(target, widget)
        return self.outside()

    def _apply(self, form, widget):
        """setRowVisible does not show a row whose widgets a move between the card and the dialog left hidden
        (a widget given another parent is hidden until shown): they are shown by hand."""
        flag = self.wanted.get(widget, True)
        form.setRowVisible(widget, flag)
        if flag:
            widget.setVisible(True)
            label = self.labels.get(widget)
            if label is not None:
                label.setVisible(True)

    def show(self, widget, flag):
        self.wanted[widget] = bool(flag)
        form = self.form_of(widget)
        if form is not None:
            self._apply(form, widget)

    def visible(self, widget):
        """Shown in its place (the card or the dialog) — what the program and the task want."""
        return self.wanted.get(widget, True)

    def shown_outside(self, widget):
        return self.visible(widget) and self.form_of(widget) is self.form

    def label(self, widget):
        return self.labels.get(widget)

    def key_of(self, widget):
        return next((k for k, w in self.rows if w is widget), None)

    # -- «Поля…» -----------------------------------------------------------------------------------------------------
    def title(self, key):
        if key in self.titles:
            return tr(self.titles[key])
        widget = next((w for k, w in self.rows if k == key), None)
        if isinstance(widget, QCheckBox) and widget.text():
            return widget.text()
        label = self.labels.get(widget)
        return label.text() if label is not None and label.text() else key

    def menu(self, parent=None):
        """Checkable items: the fields shown in the card; then the default choice."""
        menu = QMenu(parent)
        menu.setToolTipsVisible(True)
        heading = menu.addAction(tr('Показывать в «Постановке задачи»:'))
        heading.setEnabled(False)
        for key in self.movable:
            action = menu.addAction(self.title(key))
            action.setCheckable(True)
            action.setChecked(key in self.chosen)
            action.setData(key)
            action.toggled.connect(lambda flag, k=key: self.toggle(k, flag))
        menu.addSeparator()
        menu.addAction(tr('Как по умолчанию'), self.reset)
        return menu


def task_form_note():
    return tr('Здесь — поля, убранные из «Постановки задачи». Какие из них держать в карточке, выбирается кнопкой '
              '«Поля…» внизу карточки.')
