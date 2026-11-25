"""Changes of the content of a structure in Compass: «Проверить структуру…», the solvent round it, the isotopes,
a proton added, removed or moved. Methods of StructureTool (self is the tool; the window only through its port
self.w), kept here to make structure_actions.py shorter.

Split off modules/compass/actions/structure_actions.py (0.222.29).
"""

from PySide6.QtWidgets import QDialog, QLabel
from azimuth.i18n import tr


# -- the check, the solvent, the protons (modules/compass/chemistry/structure_check.py) -------------------
def check_structure(self):
    """«Проверить структуру…»: what ORCA would refuse or what looks like a slip — a window with the list; the atoms
    of the remarks are selected on the model. -> [Problem]."""
    from modules.compass.chemistry import structure_check as sc

    molecule = self.w.coordinate_tool.table_molecule()
    if not molecule.atoms:
        self.w.notify(tr('Нечего проверять: структура пустая.'))
        return []
    charge, multiplicity = self.w.charge.value(), self.w.spin.value()
    problems = sc.check(molecule, charge, multiplicity)
    if not problems:
        self.w.notify(tr('Проверка структуры: замечаний нет ✓ (заряд {}, мультиплетность {}).').format(
            charge, multiplicity), 8000)
        return problems
    marks = {'error': '✕', 'warning': '!', 'note': '·'}
    lines = [tr('Заряд {}, мультиплетность {}, атомов {}.').format(charge, multiplicity, len(molecule.atoms)), '']
    lines += [f'{marks[p.level]}  {p.text}' for p in problems]
    lines += ['', tr('✕ — ORCA этого не примет; ! — похоже на ошибку построения; · — проверьте, так ли задумано. '
                     'Атомы замечаний выделены на модели.')]
    chosen = sorted({k for p in problems for k in p.atoms})
    if chosen:
        self.w.viewer.set_selection(chosen)
    self._report(tr('Проверка структуры'), '\n'.join(lines))
    return problems


def solvate_dialog(self, solvent=None, count=None, mode='shell'):
    """«Окружить растворителем…»: the solvent and where — mode 'shell' puts a molecule on every free place of the
    first shell and nothing more; 'around' — count molecules round the structure at random. With solvent given — at
    once (tests). In the window: «Убрать растворитель» too. -> the number placed."""
    from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QFormLayout, QSpinBox

    from modules.compass.chemistry import library, structure_check as sc

    if solvent is None:
        box = QDialog(self.w.widget)
        box.setWindowTitle(tr('Окружить растворителем'))
        form = QFormLayout(box)
        kind = QComboBox()
        for key, name in sc.SOLVENTS:
            if key in library.keys():
                kind.addItem(tr(name), key)
        where = QComboBox()
        where.addItem(tr('Первая координационная сфера'), 'shell')
        where.addItem(tr('Вокруг всей молекулы, случайно'), 'around')
        many = QSpinBox()
        many.setRange(1, 60)
        many.setValue(8)
        from azimuth.ui import help_button
        from modules.compass.actions.style_form import row as one_row

        # the explanation is behind a «?» next to the choice
        explained = help_button(
            tr('Первая координационная сфера: на каждую неподелённую пару структуры (по две у кислорода, одна у '
               'азота) — донор растворителя, к каждому O–H и N–H — его акцептор, на расстоянии водородной связи. '
               'Молекул — сколько встанет; число скажет сообщение.') + '\n\n'
            + tr('Вокруг всей молекулы, случайно: заданное число молекул, без наложений.') + '\n\n'
            + tr('Дальше — оптимизация (xtb или ORCA). Неявный растворитель (CPCM) — в параметрах расчёта.'),
            tr('Где'))
        form.addRow(tr('Растворитель'), kind)
        form.addRow(tr('Где'), one_row(where, explained, stretch=False))
        form.addRow(tr('Молекул'), many)

        def explain(*_):
            many.setEnabled(where.currentData() != 'shell')  # the first shell takes as many as it has places

        where.currentIndexChanged.connect(explain)
        explain()
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        # the solvent can be removed from the same window
        remove = buttons.addButton(tr('Убрать растворитель'), QDialogButtonBox.ButtonRole.ResetRole)
        # the window stays open; the solvent goes from the model at once
        remove.clicked.connect(lambda: self.remove_solvent())
        buttons.accepted.connect(box.accept)
        buttons.rejected.connect(box.reject)
        form.addRow(buttons)
        if box.exec() != QDialog.DialogCode.Accepted:
            return None
        solvent, count, mode = kind.currentData(), many.value(), where.currentData()
    shell = mode == 'shell'
    piece = library.molecule(solvent)
    placed = []
    report = {}

    def put(molecule):
        wanted = sc.shell_places(molecule, piece) if shell else int(count or 0)
        result, done = sc.solvate(molecule, piece, wanted, shell=shell, around=not shell, report=report)
        placed.append(done)
        return result

    name = tr(dict(sc.SOLVENTS).get(solvent, solvent))
    if not self._change(put):
        return None
    done = placed[0] if placed else 0
    if shell:
        free, before = report.get('places', 0), report.get('taken', 0)
        if free + before == 0:
            message = tr('Первая координационная сфера ({}): у структуры нет центров для водородной связи с этим '
                         'растворителем — ничего не поставлено.').format(name)
        else:
            message = tr('Первая координационная сфера ({}): поставлено молекул {} из {} мест (акцепторы O, N и '
                         'группы O–H, N–H структуры).').format(name, done, free + before)
            if before:
                message += ' ' + tr('Уже занято прежним растворителем: {}.').format(before)
            if done < free:
                message += ' ' + tr('Свободным местам ({}) мешают соседние молекулы.').format(free - done)
        self.w.notify(message, 15000)
        return done
    message = tr('Добавлено молекул растворителя ({}): {}.').format(name, done)
    if done < int(count or 0):
        message += ' ' + tr('Больше не поместилось без наложений.')
    self.w.notify(message, 9000)
    return done


def remove_solvent(self):
    """«Убрать растворитель»: the molecules of a solvent round the structure taken away in one undoable step."""
    from modules.compass.chemistry import structure_check as sc

    molecule = self.w.coordinate_tool.table_molecule()
    if not molecule.atoms:
        return 0
    _, count = sc.without_solvent(molecule)
    if not count:
        self.w.notify(tr('Растворителя вокруг структуры нет.'))
        return 0
    if not self._change(lambda m: sc.without_solvent(m)[0]):
        return 0
    self.w.notify(tr('Убрано молекул растворителя: {}.').format(count), 7000)
    return count


def isotope_dialog(self, mass=None):
    """«Изотопы выделенных атомов…»: the selected atoms (one element) get an isotope — or the usual one back
    (mass 0). With mass given — at once (tests). The isotopes are of the calculation (Calculation.isotopes): ORCA
    writes «M = …» after their coordinates; the frequencies and the thermochemistry follow. -> {index: mass}."""
    from PySide6.QtWidgets import QComboBox, QDialogButtonBox, QFormLayout

    from azimuth.core import ISOTOPES, isotope_masses

    molecule = self.w.coordinate_tool.table_molecule()
    chosen = sorted(self.w.viewer.selected)
    symbols = {molecule.atoms[k].symbol for k in chosen}
    if not chosen or len(symbols) != 1:
        self.w.notify(tr('Выделите атомы одного элемента — им будет задан изотоп.'))
        return None
    symbol = symbols.pop()
    if symbol not in ISOTOPES:
        self.w.notify(tr('Для {} изотопы в программе не заданы.').format(symbol))
        return None
    current = isotope_masses(self.w._isotopes, molecule)
    if mass is None:
        box = QDialog(self.w.widget)
        box.setWindowTitle(tr('Изотопы'))
        form = QFormLayout(box)
        kind = QComboBox()
        kind.addItem(tr('обычный (природная смесь)'), 0.0)
        for name, value in ISOTOPES[symbol]:
            kind.addItem(f'{name} · {value:.6f} {tr("а. е. м.")}', value)
        now = current.get(chosen[0])
        if now:
            kind.setCurrentIndex(max(0, kind.findData(now)))
        form.addRow(tr('Атомов {}: {}').format(symbol, len(chosen)), kind)
        note = QLabel(tr('Масса — только для ORCA: она пишется после координат атома («M = …»); частоты, '
                         'термохимия и ИК-спектр считаются с ней. Геометрия и энергия от изотопа не меняются.'))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        form.addRow(note)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(box.accept)
        buttons.rejected.connect(box.reject)
        form.addRow(buttons)
        if box.exec() != QDialog.DialogCode.Accepted:
            return None
        mass = float(kind.currentData() or 0.0)
    return self.set_isotopes(chosen, mass)


def own_isotope_mass(self, indices, mass=None):
    """«Своя масса…» of «Изотоп»: a mass in u typed by the user (any isotope, a rare or radioactive one)."""
    from PySide6.QtWidgets import QInputDialog

    if not indices:
        return None
    if mass is None:
        symbol = self.w.molecule.atoms[indices[0]].symbol
        from azimuth.core import isotope_masses
        from azimuth.isotope_table import STABLE

        start = isotope_masses(self.w._isotopes, self.w.molecule).get(indices[0])
        if not start:  # the most abundant isotope as the start
            start = max(STABLE.get(symbol, ((0, 1.0, 1.0),)), key=lambda item: item[2])[1]
        value, ok = QInputDialog.getDouble(self.w.widget, tr('Своя масса'),
                                           tr('Масса атома {}, а. е. м.:').format(symbol), float(start), 0.5, 400.0,
                                           6)
        if not ok:
            return None
        mass = value
    return self.set_isotopes(indices, float(mass))


def set_isotopes(self, indices, mass):
    """The atoms indices get the isotope of mass (0 — the usual mass again): Calculation.isotopes of the window, the
    labels of the model (D, ¹³C …), the input of Sextant. -> {index: mass} of all the isotopes now."""
    from azimuth.core import isotope_masses, isotope_name, isotope_text

    molecule = self.w.coordinate_tool.table_molecule()
    current = isotope_masses(self.w._isotopes, molecule)
    for k in indices:
        if mass:
            current[k] = float(mass)
        else:
            current.pop(k, None)
    self.w._isotopes = isotope_text(current, molecule)
    changed = getattr(self.w.widget, 'settings_changed', None)
    if callable(changed):
        changed()  # the input of Sextant follows
    self.w.viewer.update()
    names = ', '.join(f'{molecule.atoms[k].symbol}{k + 1}' for k in indices)
    if mass:
        name = isotope_name(molecule.atoms[indices[0]].symbol, float(mass))
        self.w.notify(tr('{} — теперь {} (масса {:.4f}). Атомов с изотопами: {}.').format(
            names, name, float(mass), len(current)), 9000)
    else:
        self.w.notify(tr('{} — снова обычная масса. Атомов с изотопами: {}.').format(names, len(current)), 7000)
    return current


def _one_chosen(self, what):
    chosen = list(self.w.viewer.selected)
    if len(chosen) != 1:
        self.w.notify(tr('Выделите один атом — {}.').format(tr(what)))
        return None
    return chosen[0]


def add_proton(self):
    from modules.compass.chemistry import structure_check as sc

    index = self._one_chosen('куда поставить протон')
    if index is None:
        return False
    made = []
    before = self.w.charge.value()  # the new composition sets the charge by the bonds (Sextant) — from the old one
    if not self._change(lambda m: (made.append(sc.protonate(m, index)), made[-1][0])[1]):
        return False
    self.w.charge.setValue(before + 1)
    self.w.viewer.set_selection([made[-1][1]])
    self.w.notify(tr('Протон добавлен; заряд молекулы {}.').format(self.w.charge.value()), 7000)
    return True


def remove_proton(self):
    from modules.compass.chemistry import structure_check as sc

    index = self._one_chosen('водород или атом, с которого снять протон')
    if index is None:
        return False
    made = []
    before = self.w.charge.value()  # the new composition sets the charge by the bonds (Sextant) — from the old one
    if not self._change(lambda m: (made.append(sc.deprotonate(m, index)), made[-1][0])[1]):
        return False
    self.w.charge.setValue(before - 1)
    if made[-1][1] is not None:
        self.w.viewer.set_selection([made[-1][1]])
    self.w.notify(tr('Протон снят; заряд молекулы {}.').format(self.w.charge.value()), 7000)
    return True


def move_proton(self):
    from modules.compass.chemistry import structure_check as sc

    chosen = list(self.w.viewer.selected)
    if len(chosen) != 2:
        self.w.notify(tr('Выделите водород и атом, к которому его перенести.'))
        return False
    made = []
    if not self._change(lambda m: (made.append(sc.move_proton(m, chosen[0], chosen[1])), made[-1][0])[1]):
        return False
    self.w.viewer.set_selection([made[-1][1]])
    self.w.notify(tr('Протон перенесён — таутомер; заряд прежний.'), 7000)
    return True
