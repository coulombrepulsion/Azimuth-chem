"""The form of the crystal calculation (QePanel): its fields, the rows shown for the task and the program, the
processes and memory of this computer. Methods of QePanel (self is the panel), kept here to make qe_window.py shorter.

Split off modules/compass/actions/qe_window.py (0.222.29).
"""

import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.actions.qe_common import task_title


# -- the controls ------------------------------------------------------------------------------------------------
def _make_controls(self):
    from modules.sextant import qe_inputs

    def spin(lo, hi, value, step=1, decimals=None, suffix='', tip=''):
        box = QDoubleSpinBox() if decimals is not None else QSpinBox()
        box.setRange(lo, hi)
        if decimals is not None:
            box.setDecimals(decimals)
        box.setSingleStep(step)
        box.setValue(value)
        if suffix:
            box.setSuffix(suffix)
        if tip:
            box.setToolTip(tip)
        return box

    def combo(items, tip=''):
        box = QComboBox()
        for key, title in items:
            box.addItem(tr(title), key)
        if tip:
            box.setToolTip(tip)
        return box

    self.note = QLabel(tr('Периодический расчёт ячейки кристалла плоскими волнами (pw.x, функционал PBE, псевдопотенциалы '
                          'SSSP efficiency, обрезки — из их таблицы). Считается одна ячейка файла, не блок на экране.'))
    self.note.setWordWrap(True)
    self.note.setObjectName('subtitle')
    # + the bands and the density of states; the word of the program after the name (task_title)
    self.task = QComboBox()
    for t in qe_inputs.ALL_TASKS:
        self.task.addItem(task_title(t, 'qe'), t)
    # the program of the crystal — Quantum ESPRESSO (plane waves) or CP2K (Gaussians and plane waves, Γ)
    from modules.sextant import cp2k_inputs

    self.program_box = combo([('qe', 'Quantum ESPRESSO'), ('cp2k', 'CP2K')],
                             tr('Кристалл считается периодически: Quantum ESPRESSO — плоские волны, k-точки, зоны и '
                                'плотность состояний; CP2K — гауссовы базисы с плоскими волнами (GPW), Γ-точка, быстрее '
                                'на больших ячейках (молекулярные кристаллы). ORCA и другие молекулярные программы '
                                'периодических расчётов не делают.'))
    self.basis = combo(list(cp2k_inputs.BASES.items()),
                       tr('Базис MOLOPT: SR (короткодиффузный) — для всех элементов и для твёрдых тел; полные DZVP, '
                          'TZVP, TZV2P — только H C N O F Si P S Cl, для молекулярных кристаллов'))
    # the functional of CP2K (its pseudopotentials: GTH-PBE, for BLYP — GTH-BLYP)
    self.cp2k_functional = combo(list(cp2k_inputs.FUNCTIONALS.items()),
                                 tr('PBE — по умолчанию; PBEsol — точнее параметры решётки твёрдых тел; revPBE и BLYP '
                                    '— обычны для молекулярных кристаллов и воды (с поправкой D3). Псевдопотенциалы '
                                    'GTH-PBE, для BLYP — GTH-BLYP. GFN1-xTB — полуэмпирика в сотни раз быстрее DFT, со '
                                    'своей поправкой D3: предварительная оптимизация больших ячеек'))
    self.cutoff = spin(100, 2000, 400, 50, 0, ' Ry', tr('CUTOFF — сетка плотности'))
    self.rel_cutoff = spin(20, 200, 50, 10, 0, ' Ry', tr('REL_CUTOFF — какие гауссианы на какую сетку'))
    self.temperature = spin(10, 5000, 300, 50, 0, ' K', tr('Электронная температура размытия Ферми — Дирака'))
    self.cp2k_vdw = combo(list(cp2k_inputs.VDW_NAMES.items()), tr('Дисперсионная поправка Гримме'))
    self.cp2k_vdw.setCurrentIndex(self.cp2k_vdw.findData('d3bj'))
    self.eps_scf = combo([(1e-6, 'обычная (EPS_SCF 10⁻⁶)'), (1e-7, 'точная (10⁻⁷)'), (1e-5, 'грубая (10⁻⁵)')],
                         tr('EPS_SCF — сходимость самосогласования'))
    # the grid by its spacing or n1 × n2 × n3 given
    self.kmode = combo([('spacing', 'по шагу'), ('grid', 'вручную')], tr('Сетка k-точек: по шагу (n = ⌈2π|b|/Δk⌉) или заданная'))
    self.spacing = spin(0.05, 1.0, qe_inputs.SPACING, 0.05, 2, ' Å⁻¹', tr('Шаг сетки k-точек: меньше — гуще сетка, точнее и дольше'))
    self.grid = [spin(1, 64, 4, tip=tr('Число k-точек вдоль оси')) for _ in range(3)]
    self.processes = spin(1, max(1, os.cpu_count() or 1), 1)
    self.processes.setSuffix(tr(' проц.'))
    # as wide as for the server (up to 256) from the start: the width of a spin box follows its largest value, and the
    # fields grew when «Сервер» was chosen (the owner, 2026-11-24)
    local = self.processes.maximum()
    self.processes.setMaximum(256)
    self.processes.setMinimumWidth(self.processes.sizeHint().width())
    self.processes.setMaximum(local)
    # the memory per process
    # (the --mem of a job on the server; here — what pw.x may take), both advised for this computer
    self.memory = spin(100, 1000000, 1000, 500, suffix=tr(' МБ'))
    self._resources_touched = False
    self.apply_machine()
    for box in (self.processes, self.memory):
        box.editingFinished.connect(lambda: setattr(self, '_resources_touched', True))
    self.where = QComboBox()  # this computer or the server of «Сервер…» (SLURM), when one is set up
    self.where_label = QLabel(tr('Где'))
    self.update_where()
    self.where.currentIndexChanged.connect(lambda _: self.where_changed())
    # a centred lattice in its primitive cell — m times fewer atoms (crystal.primitive)
    self.primitive = QCheckBox()
    self.primitive.setToolTip(tr('Центрированная решётка (F, I, A, B, C, R) в примитивной ячейке — та же структура, '
                                 'меньше атомов, расчёт в разы быстрее; энергия — на примитивную ячейку'))
    # a supercell along one axis or several (crystal.supercell), after the primitive cell
    self.supercell = [spin(1, 10, 1, tip=tr('Повторений ячейки вдоль оси')) for _ in range(3)]
    self.cut_auto = QCheckBox(tr('по таблице SSSP'))
    self.cut_auto.setChecked(True)
    self.ecutwfc = spin(10, 300, 40, 5, 0, ' Ry', tr('ecutwfc — обрезка волновых функций'))
    self.ecutrho = spin(40, 2400, 320, 20, 0, ' Ry', tr('ecutrho — обрезка плотности (обычно 8–12 × ecutwfc для ультрамягких)'))
    self.occupations = combo(list(qe_inputs.OCCUPATIONS.items()))
    self.smearing = combo(list(qe_inputs.SMEARINGS.items()))
    self.degauss = spin(0.001, 0.2, qe_inputs.DEGAUSS, 0.005, 3, ' Ry', tr('degauss — ширина размытия'))
    # the functional (PBEsol — its own SSSP library; the vdW-DF family) and the charge of the cell
    self.functional = combo(list(qe_inputs.FUNCTIONALS.items()),
                            tr('PBE — по умолчанию; PBEsol — точнее параметры решётки твёрдых тел (свои псевдопотенциалы '
                               'SSSP PBEsol, скачиваются один раз); нелокальные vdW-DF2, rev-vdW-DF2, vdW-DF-cx и rVV10 '
                               'сами учитывают дисперсию — для молекулярных и слоистых кристаллов; гибридные PBE0 и '
                               'HSE06 точнее дают щель, но в десятки раз дороже и только для «Энергии»'))
    self.pseudo_button = action_button(tr('Скачать псевдопотенциалы'), self.download_library, 'download')
    self.pseudo_button.setToolTip(tr('Библиотека SSSP для этого функционала — около 60 МБ, один раз'))
    self.charge = spin(-8, 8, 0, 1, 0, '', tr('Заряд ячейки: +1 — на один электрон меньше; заряд компенсируется '
                                              'однородным фоном (tot_charge в QE, CHARGE в CP2K)'))
    # DFT+U — «Fe 5.3, Ni 6.2» (eV; the d or f shell of the element, modules/sextant/hubbard.py)
    self.hubbard = QLineEdit()
    self.hubbard.setToolTip(tr('DFT+U: U в эВ для d- или f-оболочки, например «Fe 5.3, Ni 6.2». Нужен для оксидов и '
                               'фторидов переходных металлов, соединений Ce, U: без него PBE почти закрывает щель NiO, '
                               'MnO, FeO. U зависит от программы и проекторов — берите значение для той же программы '
                               '(QE: ortho-atomic; CP2K: Mulliken) или посчитайте (hp.x в QE). Пусто — без U'))
    self.vdw = combo(list(qe_inputs.VDW_NAMES.items()), tr('Дисперсионная поправка: для молекулярных и слоистых кристаллов '
                                                          'без неё PBE не держит упаковку'))
    self.spin = QCheckBox(tr('спин-поляризованный расчёт'))
    self.magnetization = spin(-1.0, 1.0, 0.5, 0.1, 2, '', tr('Начальная намагниченность каждого элемента (−1 … 1)'))
    # the magnetic order — all moments up, or the antiferromagnet of two sublattices (modules/sextant/
    # magnetism.py: species Ni1 and Ni2 with the moments ±)
    from modules.sextant import magnetism

    self.order = combo(list(magnetism.ORDERS.items()),
                       tr('Ферромагнитный — все моменты в одну сторону; антиферромагнитный — магнитные атомы делятся на '
                          'две подрешётки с противоположными моментами (NiO, MnO, FeO, CoO, Cr₂O₃). Ячейка должна '
                          'вмещать обе подрешётки: для NiO и MnO в примитивной ячейке — суперячейка 2 × 1 × 1 '
                          '(порядок AFM-II)'))
    self.magnetization_label = QLabel(tr('намагниченность'))
    self.magnetic_asked = set()  # the crystals whose start without spin was confirmed
    self.conv = combo([(1e-8, 'обычная (10⁻⁸ Ry на атом)'), (1e-10, 'точная (10⁻¹⁰)'), (1e-6, 'грубая (10⁻⁶)')],
                      tr('conv_thr — сходимость самосогласования'))
    self.forces = spin(0.0, 0.1, 0.0, 0.0001, 4, ' Ry/bohr', tr('forc_conv_thr; 0 — по умолчанию pw.x (10⁻³)'))
    self.pressure = spin(0.0, 10.0, 0.0, 0.1, 1, tr(' кбар'), tr('press_conv_thr; 0 — по умолчанию pw.x (0.5 кбар)'))
    self.forces.setSpecialValueText(tr('по умолчанию'))
    self.pressure.setSpecialValueText(tr('по умолчанию'))
    # the editor of the program (azimuth/text_editor.py, as AkelPad); «!» — a comment of pw.x
    from azimuth.text_editor import CodeEdit, EditorPane

    self.preview = CodeEdit(comment='!')
    self.preview.set_language('qe')
    self.preview_pane = EditorPane(self.preview)
    self.edited_note = QLabel(tr('Файл изменён вручную — при запуске пойдёт он; настройки его не меняют.'))
    self.edited_note.setWordWrap(True)
    self.edited_note.setObjectName('subtitle')
    self.edited_note.hide()
    self.reset_button = action_button(tr('Собрать файл заново по настройкам'), self.reset_input, 'undo')
    self.reset_button.hide()
    self.status = QLabel('')
    self.status.setWordWrap(True)
    self.summary = QLabel('')
    self.summary.setWordWrap(True)
    self.run_button = action_button(tr('Запустить расчёт'), self.run_clicked, 'play')  # or the batch
    self.stop_button = action_button(tr('Остановить'), self.stop, 'stop')
    self.open_button = action_button(tr('Открыть оптимизированную ячейку'), self.open_relaxed, 'crystal')
    self.plot_button = action_button(tr('Показать график'), self.show_plot, 'spectrum')
    self.aim_button = action_button(tr('Связи по AIM (Multiwfn)'), self.show_aim, 'bond-orders')
    self.aim_button.hide()
    self.charges_button = action_button(tr('Заряды CM5 и Хиршфельда (Multiwfn)'), self.show_charges, 'table')
    self.charges_button.hide()
    self.stop_button.setEnabled(False)
    self.open_button.setEnabled(False)
    self.plot_button.hide()
    # every field may shrink with the column — no fixed widths
    from PySide6.QtWidgets import QSizePolicy

    for box in (self.spacing, self.ecutwfc, self.ecutrho, self.degauss, self.magnetization, self.forces, self.pressure,
                self.processes, self.memory, self.kmode, self.smearing, *self.grid, *self.supercell):
        box.setMinimumWidth(48)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
    for box in (self.task, self.occupations, self.vdw, self.conv, self.where, self.program_box, self.basis,
                self.cp2k_vdw, self.eps_scf, self.kmode, self.functional, self.cp2k_functional):  # every list — a
                # long item no longer widens the column
        box.setMinimumWidth(60)
        box.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
        box.setMinimumContentsLength(8)
    for box in (self.degauss, self.spacing, self.memory, self.processes):
        box.setMinimumWidth(96)
    self.degauss.setMinimumWidth(118)  # «0.020 Ry» whole next to the kind of smearing
    self.smearing.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
    self.smearing.setMinimumContentsLength(6)
    for box in (self.primitive, self.cut_auto, self.spin):
        box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)  # long words are cut, not the column


def rows(self):
    """(title, widget) of the settings, in the order of the form — the same for the dialog and Sextant."""
    def line(*items):
        box = QWidget()
        row = QHBoxLayout(box)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        for item in items:
            row.addWidget(item) if not isinstance(item, str) else row.addWidget(QLabel(item))
        row.addStretch(1)
        return box

    if not hasattr(self, '_rows'):
        self.grid_line = line(*self.grid)
        self.cut_line = line(self.ecutwfc, self.ecutrho)
        self.smear_line = line(self.smearing, self.degauss)
        self.spin_line = line(self.order, self.magnetization_label, self.magnetization)  # + the order
        self.relax_line = line(self.forces, self.pressure)
        self.k_line = line(self.kmode, self.spacing)
        self.cp2k_cut_line = line(self.cutoff, self.rel_cutoff)
        self.temperature_line = line(QLabel(tr('температура')), self.temperature)
        self.functional_line = line(self.functional, self.pseudo_button)
        self._rows = [
            (tr('Программа'), self.program_box),
            (tr('Задача'), self.task),
            (tr('Сетка k'), self.k_line),
            ('', self.grid_line),
            (tr('Ячейка'), self.primitive),
            (tr('Суперячейка'), line(self.supercell[0], '×', self.supercell[1], '×', self.supercell[2])),
            (tr('Базис'), self.basis),
            (tr('Обрезки'), self.cut_auto),
            ('', self.cut_line),
            (tr('Сетка плотности'), self.cp2k_cut_line),
            (tr('Функционал'), self.functional_line),
            (tr('Функционал '), self.cp2k_functional),  # CP2K
            (tr('Заряд ячейки'), self.charge),
            ('DFT+U', self.hubbard),
            (tr('Заполнение'), self.occupations),
            ('', self.smear_line),
            ('', self.temperature_line),
            (tr('Дисперсия'), self.vdw),
            (tr('Дисперсия '), self.cp2k_vdw),
            (tr('Спин'), self.spin),
            ('', self.spin_line),
            (tr('Сходимость SCF'), self.conv),
            (tr('Сходимость SCF '), self.eps_scf),
            (tr('Пороги оптимизации'), self.relax_line),
            (tr('Ресурсы'), line(self.processes, '×', self.memory)),
        ]
        if getattr(self, 'where_in_form', True):  # Sextant: the switches next to «Запустить расчёт»
            self._rows.append((tr('Где считать'), self.where))
    return self._rows


def apply_machine(self, owner=None):
    """The processes and the memory per process of the window (advised for this computer, as for a molecule)
    or of advice.recommended; kept once changed by hand."""
    if self._resources_touched:
        return False
    owner = owner or self.owner
    cores, memory = getattr(owner, 'cores', None), getattr(owner, 'memory', None)
    if cores is not None and memory is not None:
        values = cores.value(), memory.value()
    else:
        from modules.sextant import advice

        machine = advice.machine()
        values = advice.recommended(machine) if machine is not None else (1, 1000)
    if self.on_server() if hasattr(self, 'where') and self.where.count() else False:
        return False
    self.processes.setValue(min(values[0], self.processes.maximum()))
    self.memory.setValue(values[1])
    return True


def _compact_layout(self):
    from PySide6.QtWidgets import QFormLayout, QGroupBox, QScrollArea

    layout = QVBoxLayout(self)
    layout.setContentsMargins(0, 0, 0, 0)
    self.top_row = QHBoxLayout()
    layout.addLayout(self.top_row)
    layout.addWidget(self.note)
    top = QHBoxLayout()
    settings = QGroupBox(tr('Настройки Quantum ESPRESSO'))
    form = QFormLayout(settings)
    for title, widget in self.rows():
        form.addRow(title, widget)
    self.form = form
    self.update_where()
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(settings)
    scroll.setMinimumWidth(440)
    top.addWidget(scroll, 3)
    right = QVBoxLayout()
    right.addWidget(self.preview_pane, 1)
    right.addWidget(self.edited_note)
    right.addWidget(self.reset_button)
    top.addLayout(right, 4)
    layout.addLayout(top, 1)
    layout.addWidget(self.status)
    layout.addWidget(self.summary)
    buttons = QHBoxLayout()
    for b in (self.run_button, self.stop_button, self.open_button, self.plot_button, self.aim_button,
              self.charges_button):
        buttons.addWidget(b)
    buttons.addStretch(1)
    self.buttons = buttons  # the dialog adds «Закрыть»
    layout.addLayout(buttons)


def show_rows(self):
    """Only the rows the settings use: the grid by hand, the smearing, the thresholds of a relaxation; the cutoffs
    and the magnetization grey when not used."""
    from modules.sextant import qe_inputs

    self.rows()
    cp2k = self.program == 'cp2k'
    manual = self.kmode.currentData() == 'grid'
    calculation = qe_inputs.TASKS.get(self.task.currentData())
    self.spacing.setVisible(not manual)

    self.pressure.setVisible(calculation == 'vc-relax')
    smear = self.occupations.currentData() != 'fixed'
    xtb = cp2k and self.cp2k_functional.currentData() == 'GFN1-XTB'  # no basis, grid, D3 choice or U
    shown = {self.grid_line: manual and not cp2k, self.smear_line: smear and not cp2k,
             self.relax_line: calculation in ('relax', 'vc-relax') and not cp2k,
             self.cut_line: not self.cut_auto.isChecked() and not cp2k,
             # the spin and its order for CP2K too (not GFN1-xTB); the starting magnetization is of pw.x
             self.spin_line: self.spin.isChecked() and not xtb, self.magnetization: not cp2k,
             self.magnetization_label: not cp2k,
             # the rows of one program only
             self.k_line: not cp2k, self.cut_auto: not cp2k, self.vdw: not cp2k, self.spin: not xtb,
             self.functional_line: not cp2k, self.cp2k_functional: cp2k,
             self.conv: not cp2k, self.basis: cp2k and not xtb, self.cp2k_cut_line: cp2k and not xtb,
             self.temperature_line: cp2k and smear, self.cp2k_vdw: cp2k and not xtb, self.eps_scf: cp2k,
             self.hubbard: not xtb}
    # Sextant keeps some rows in «Дополнительные настройки…» (extra_forms) — hidden there as rows too
    forms = [f for f in [getattr(self, 'form', None), *getattr(self, 'extra_forms', ())] if f is not None]
    for widget, flag in shown.items():
        holder = next((f for f in forms if f.indexOf(widget) >= 0), None)
        if holder is not None:
            holder.setRowVisible(widget, flag)
        else:
            widget.setVisible(flag)
