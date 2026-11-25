"""Compass: the «Кристалл» window — the cell, the group, the block of cells to build, the surface (hkl), the
contacts. What it does with the model is CrystalTool (crystal_actions.py); theory: modules/compass/chemistry/crystal.py.

Split off modules/compass/actions/crystal_actions.py (0.222.29).
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QPlainTextEdit,
    QDialog,
    QDoubleSpinBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QVBoxLayout,
)
from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_contacts as cc
from modules.compass.chemistry import crystal_symmetry as cs
from modules.compass.chemistry import surface as sf
from azimuth.core import Atom, Molecule
from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.actions.crystal_contacts_window import ContactsWindow


def narrow(box):
    """A number box of the narrow panel — it may shrink to its digits."""
    box.setMinimumWidth(56)
    box.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
    return box


def alive(widget):
    """The Qt object of widget still there (not deleted)."""
    if widget is None:
        return False
    try:
        from shiboken6 import isValid
    except ImportError:  # pragma: no cover
        return True
    return isValid(widget)


class CrystalWindow(QDialog):
    def __init__(self, owner, data, name):
        super().__init__(owner)
        self.owner, self.data = owner, data
        self.setWindowTitle(tr('Кристалл · ') + name)
        # the settings scroll inside the window, the buttons stay under them; the window no taller than the screen
        from PySide6.QtWidgets import QFrame, QScrollArea, QWidget

        outer = QVBoxLayout(self)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setFrameShape(QFrame.Shape.NoFrame)
        # no sideways scroll —
        # the panel is narrow, its rows are folded to fit it
        self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        body = QWidget()
        layout = QVBoxLayout(body)
        layout.setContentsMargins(0, 0, 0, 0)
        self.scroll.setWidget(body)
        outer.addWidget(self.scroll, 1)
        content = cr.unit_cell(data)
        formula = Molecule('', tuple(Atom(s, 0, 0, 0) for s, *_ in content)).formula
        c = data.cell
        lines = [
            f'<b>{data.title or name}</b> · {formula}' + (f' · {data.space_group}' if data.space_group else ''),
            tr(f'a = {c.a:.4f} Å, b = {c.b:.4f} Å, c = {c.c:.4f} Å'),
            tr(f'α = {c.alpha:.3f}°, β = {c.beta:.3f}°, γ = {c.gamma:.3f}°, V = {c.volume():.2f} Å³'),
            tr(f'В ячейке атомов: {len(content)} (позиций в файле: {len(data.sites)}, операций симметрии: {len(data.operations)})'),
        ] + list(data.notes)
        # the space group from the operations, Z, the density; the molecules across the faces of the cell
        try:
            self.symmetry = cs.analyse(data)
        except ValueError as exc:
            self.symmetry = None
            lines.append(str(exc))
        self.groups = cr.disorder_groups(data)  # one part of a disorder by default
        try:
            self.packing = cs.molecules(cr.main_part(data))
        except ValueError as exc:
            self.packing = None
            lines.append(str(exc))
        s = self.symmetry
        if s is not None:
            group = data.space_group or '—'
            number = tr(' (№ {})').format(s.number) if s.number else ''
            lines.insert(1, tr('Пространственная группа {} · система {} · точечная группа {} · решётка {}').format(
                group + number, tr(s.system) if s.system else '—', s.point_group or '—', s.centring))
            z_prime = str(s.z_prime) if s.z_prime else '—'
            z = f'{s.z:g}' if isinstance(s.z, float) else str(s.z)
            density = tr(', ρ = {} г/см³').format(f'{s.density:.3f}') if s.density else ''
            lines.insert(2, tr('Формульная единица {}, Z = {}, Z′ = {}{}').format(s.formula, z, z_prime, density))
            lines += list(s.notes)
        if self.packing is not None and self.packing.text:
            lines.append(self.packing.text)
        try:
            fill = cs.packing_coefficient(cr.main_part(data))
            lines.append(tr('Коэффициент упаковки {} — доля ячейки внутри ван-дер-ваальсовых сфер атомов (радиусы Бонди)').format(
                f'{fill:.3f}'))
        except (ValueError, MemoryError):
            pass
        # the name, the group
        # and Z always; the rest of the cell and the packing, the block, the operations, the surface and the view — in
        # sections that fold (section), the block open
        head = 3 if s is not None else 1
        info = QLabel('<br>'.join(lines[:head]))
        info.setWordWrap(True)
        layout.addWidget(info)
        more = self.section(layout, tr('Ячейка и упаковка'))
        details = QLabel('<br>'.join(lines[head:]))
        details.setWordWrap(True)
        more.addWidget(details)
        if data.space_group and self.symmetry is not None and self.symmetry.system:
            symbol_row = QHBoxLayout()
            self.symbol_button = QPushButton(tr('Что значит символ {}…').format(data.space_group))
            self.symbol_button.setToolTip(tr('Буква решётки и каждая позиция символа: какая ось или плоскость и вдоль '
                                             'какого направления'))
            self.symbol_button.clicked.connect(self.explain_symbol)
            symbol_row.addWidget(self.symbol_button)
            symbol_row.addStretch(1)
            more.addLayout(symbol_row)
        grid = QGridLayout()
        # the label over the three boxes, the boxes narrow
        cells = QVBoxLayout()
        cells.setSpacing(4)
        cells.addWidget(QLabel(tr('Ячеек вдоль a, b, c')))
        row = QHBoxLayout()
        self.counts = []
        for _ in range(3):
            box = QSpinBox()
            box.setRange(1, 10)
            box.setValue(1)
            narrow(box)
            self.counts.append(box)
            row.addWidget(box)
        cells.addLayout(row)
        grid.addLayout(cells, 0, 0, 1, 2)
        self.faces = QCheckBox(tr('Атомы на гранях, рёбрах и в вершинах'))
        self.faces.setChecked(True)
        self.faces.setToolTip(tr('Повторить атомы с координатой 0 на дальних гранях блока — как на рисунках ячейки'))
        grid.addWidget(self.faces, 1, 0, 1, 2)
        self.whole = QCheckBox(tr('Целые молекулы (достроить через грани ячейки)'))
        self.whole.setToolTip(tr('Молекулы, которые грань ячейки разрезает, ставятся целиком — центр каждой внутри ячейки'))
        molecular = self.packing is not None and bool(self.packing.molecules)
        self.whole.setEnabled(molecular)
        self.whole.setChecked(molecular and not self.packing.frameworks)
        if not molecular:
            self.whole.setToolTip(tr('В этом кристалле нет отдельных молекул: связи идут через всю решётку'))
        self.whole.toggled.connect(lambda on: self.faces.setEnabled(not on))
        self.faces.setEnabled(not self.whole.isChecked())
        grid.addWidget(self.whole, 2, 0, 1, 2)
        self.one_part = QCheckBox(tr('Одна часть разупорядочения'))
        self.one_part.setToolTip(tr('Атомы разупорядоченной части {} — остальные части не ставятся').format(
            self.groups[0] if self.groups else ''))
        self.one_part.setEnabled(bool(self.groups))
        self.one_part.setChecked(bool(self.groups))
        if not self.groups:
            self.one_part.setToolTip(tr('В файле нет групп разупорядочения'))
        grid.addWidget(self.one_part, 3, 0, 1, 2)
        # a block by ranges of the fractional coordinates instead of whole cells (crystal_packing.build_range)
        self.by_range = QCheckBox(tr('Диапазон координат (доли ячейки) вместо числа ячеек'))
        self.by_range.setToolTip(tr('Атомы (или целые молекулы — по их центрам) с координатами от и до по каждой оси, '
                                    'например −0,5…1,5 вдоль a'))
        grid.addWidget(self.by_range, 4, 0, 1, 2)
        ranges = QGridLayout()  # one row an axis (six boxes in a row went past the panel)
        self.range_boxes = []
        for row_of_axis, axis in enumerate('xyz'):
            pair = []
            for column_of_box, value in enumerate((0.0, 1.0)):
                box = QDoubleSpinBox()
                box.setRange(-5.0, 6.0)
                box.setDecimals(2)
                box.setSingleStep(0.25)
                box.setValue(value)
                box.setPrefix(axis + ' ' if value == 0.0 else '… ')
                box.setEnabled(False)
                narrow(box)
                pair.append(box)
                ranges.addWidget(box, row_of_axis, column_of_box)
            self.range_boxes.append(pair)
        grid.addLayout(ranges, 5, 0, 1, 2)

        def by_range(on):
            for pair in self.range_boxes:
                for box in pair:
                    box.setEnabled(on)
            for box in self.counts:
                box.setEnabled(not on)

        self.by_range.toggled.connect(by_range)
        self.section(layout, tr('Блок ячеек'), True).addLayout(grid)
        if self.symmetry is not None and self.symmetry.operations:  # what each operation is
            box_layout = self.section(layout, tr('Операции симметрии'))
            text = QPlainTextEdit()
            text.setLineWrapMode(QPlainTextEdit.LineWrapMode.WidgetWidth)
            text.setReadOnly(True)
            text.setPlainText('\n'.join(
                f'{k}. {sf.operation_text(op)} — {d["text"]}'
                for k, (op, d) in enumerate(zip(data.operations, self.symmetry.operations), start=1)))
            text.setMinimumHeight(150)
            box_layout.addWidget(text)
        sgrid = QGridLayout()
        self.section(layout, tr('Поверхность (hkl)')).addLayout(sgrid)
        self.miller = []
        row = QHBoxLayout()
        for name, value in zip('hkl', (1, 0, 0)):
            spin = QSpinBox()
            spin.setRange(-9, 9)
            spin.setValue(value)
            spin.setPrefix(name + ' ')
            self.miller.append(spin)
            row.addWidget(spin)
        sgrid.addWidget(QLabel(tr('Индексы Миллера')), 0, 0)
        sgrid.addLayout(row, 0, 1)
        self.layers = QSpinBox()
        self.layers.setRange(1, 20)
        self.layers.setValue(3)
        sgrid.addWidget(QLabel(tr('Слоёв (шагов между плоскостями)')), 1, 0)
        sgrid.addWidget(self.layers, 1, 1)
        row = QHBoxLayout()
        self.plane = []
        for _ in range(2):
            spin = QSpinBox()
            spin.setRange(1, 6)
            spin.setValue(2)
            self.plane.append(spin)
            row.addWidget(spin)
        sgrid.addWidget(QLabel(tr('Ячеек в плоскости')), 2, 0)
        sgrid.addLayout(row, 2, 1)
        self.vacuum = QDoubleSpinBox()
        self.vacuum.setRange(0.0, 100.0)
        self.vacuum.setValue(15.0)
        self.vacuum.setSuffix(' Å')
        self.vacuum.setToolTip(tr('Промежуток вдоль нормали между пластиной и её периодическими копиями'))
        sgrid.addWidget(QLabel(tr('Вакуум')), 3, 0)
        sgrid.addWidget(self.vacuum, 3, 1)
        surface = QPushButton(tr('Построить поверхность'))
        surface.clicked.connect(self.build_surface)
        sgrid.addWidget(surface, 4, 1)
        vcolumn = self.section(layout, tr('Вид'))  # along the cell edges and the normal to (hkl)
        vrow = QHBoxLayout()
        vcolumn.addLayout(vrow)
        for axis in ('a', 'b', 'c'):
            button = QPushButton(tr('Вдоль {}').format(axis))
            button.setToolTip(tr('Смотреть вдоль ребра {} ячейки').format(axis))
            button.clicked.connect(lambda checked=False, k=axis: self.owner.crystal_tool.look_along_cell(self.data, k))
            vrow.addWidget(button)
        vrow = QHBoxLayout()  # the normal and the switches each on a row of its own (one row was too wide)
        vcolumn.addLayout(vrow)
        normal = QPushButton(tr('Вдоль нормали к (hkl)'))
        normal.setToolTip(tr('Смотреть перпендикулярно плоскостям с индексами Миллера из «Поверхности (hkl)»'))
        normal.clicked.connect(lambda: self.owner.crystal_tool.look_along_cell(
            self.data, tuple(s.value() for s in self.miller)))
        vrow.addWidget(normal)
        vrow.addStretch(1)
        vrow = vcolumn  # the switches of what is drawn, one under another
        self.elements = QCheckBox(tr('Элементы симметрии'))
        self.elements.setToolTip(tr('Оси, плоскости и центры инверсии в ячейке: повороты — сплошные, винтовые оси и '
                                    'плоскости скольжения — пунктир'))
        self.elements.setChecked(bool(getattr(self.owner.crystal_tool, 'symmetry_shown', False)))
        self.elements.toggled.connect(lambda on: self.owner.crystal_tool.set_symmetry_shown(on, self.data))
        vrow.addWidget(self.elements)
        self.lattice = QCheckBox(tr('Узлы решётки Браве'))
        self.lattice.setToolTip(tr('Узлы решётки в блоке ячеек: в вершинах — маленькие ромбы, узлы центрировки (I, F, '
                                   'A, B, C, R) — крупнее'))
        self.lattice.setChecked(bool(getattr(self.owner.crystal_tool, 'lattice_shown', False)))
        self.lattice.toggled.connect(lambda on: self.owner.crystal_tool.set_lattice_shown(on, self.data))
        vrow.addWidget(self.lattice)
        self.adp = QCheckBox(tr('Эллипсоиды смещений (50 %)'))
        has_u = any(s.u or s.u_iso > 0 for s in data.sites)
        self.adp.setEnabled(has_u)
        self.adp.setToolTip(tr('Тепловые эллипсоиды атомов из Uᵢⱼ файла: внутри — с вероятностью 50 %') if has_u
                            else tr('В файле нет параметров смещения атомов (U или B)'))
        self.adp.setChecked(has_u and bool(getattr(self.owner.crystal_tool, 'ellipsoids_shown', False)))
        self.adp.toggled.connect(lambda on: self.owner.crystal_tool.set_ellipsoids_shown(on, self.chosen()))
        vrow.addWidget(self.adp)
        self.polyhedra = QCheckBox(tr('Координационные полиэдры'))
        metals = any(s.symbol not in cs.NONMETALS for s in data.sites)
        self.polyhedra.setEnabled(metals)
        self.polyhedra.setToolTip(tr('Многогранники ближайших соседей атомов металлов (октаэдры, тетраэдры, кубы…)') if metals
                                  else tr('В кристалле нет атомов металлов'))
        self.polyhedra.setChecked(metals and bool(getattr(self.owner.crystal_tool, 'polyhedra_shown', False)))
        self.polyhedra.toggled.connect(lambda on: self.owner.crystal_tool.set_polyhedra_shown(on))
        vrow.addWidget(self.polyhedra)
        layout.addStretch(1)
        # the window is a panel beside the model (CrystalTool.dock), the model rebuilt
        # as the settings of the block change (live, after a short pause); the actions in two rows — the panel is narrow
        # the actions, «?» and «Закрыть» — one row
        actions = QHBoxLayout()
        actions.setSpacing(6)
        save = action_button(tr('Сохранить CIF…'), lambda: self.owner.crystal_tool.save_crystal_cif(), 'save')
        actions.addWidget(save)
        contacts = action_button(tr('Контакты…'), self.show_contacts, 'ruler')
        contacts.setToolTip(tr('Водородные связи и короткие контакты между молекулами кристалла'))
        actions.addWidget(contacts)
        # the calculation is set in Sextant (the arrow of a crystal, «Quantum ESPRESSO (кристалл)»); show_qe stays for
        # tests
        xrd = action_button(tr('Порошковая дифрактограмма…'), self.show_powder, 'spectrum')
        xrd.setToolTip(tr('Рентгеновская порошковая дифрактограмма с интенсивностями; наложение опытной'))
        actions.addWidget(xrd)
        outer.addLayout(actions)
        buttons = actions
        from azimuth.ui import help_button

        # long explanations go behind a «?» button
        buttons.addWidget(help_button(tr('Модель перестраивается сразу, как меняются ячейки и галочки: кнопки «Построить» '
                                         'нет. Разделы панели раскрываются щелчком по заголовку.')))
        buttons.addStretch(1)
        close = action_button(tr('Закрыть'), self.reject, 'close')
        buttons.addWidget(close)
        self.fit_width(body)
        self.fit_screen(body)
        from PySide6.QtCore import QTimer

        self.live = False  # CrystalTool.reopen_crystal turns it on once the boxes have their values
        self.rebuild_timer = QTimer(self)
        self.rebuild_timer.setSingleShot(True)
        self.rebuild_timer.setInterval(350)
        self.rebuild_timer.timeout.connect(self.rebuild)
        for box in self.counts:
            box.valueChanged.connect(self.changed)
        for pair in self.range_boxes:
            for box in pair:
                box.valueChanged.connect(self.changed)
        for check in (self.faces, self.whole, self.one_part, self.by_range):
            check.toggled.connect(self.changed)

    @staticmethod
    def section(layout, title, opened=False):
        """A section of the panel that folds — its title with an arrow, its contents under it; returns
        the layout of the contents (its .header — the title button)."""
        from PySide6.QtWidgets import QToolButton, QWidget

        header = QToolButton()
        header.setObjectName('sectionHeader')
        header.setText(title)
        header.setCheckable(True)
        header.setChecked(opened)
        header.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        header.setArrowType(Qt.ArrowType.DownArrow if opened else Qt.ArrowType.RightArrow)
        # a tinted band with a
        # blue edge for the title, the contents under it on a thin line at the left — in both themes
        header.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        header.setStyleSheet('QToolButton#sectionHeader {border: none; border-left: 3px solid #2a62b8; '
                             'background: rgba(42, 98, 184, 0.10); border-radius: 4px; font-weight: 600; '
                             'padding: 6px 8px; text-align: left; margin-top: 6px;}'
                             'QToolButton#sectionHeader:hover {background: rgba(42, 98, 184, 0.18);}')
        contents = QWidget()
        contents.setObjectName('sectionBody')
        contents.setStyleSheet('QWidget#sectionBody {border-left: 1px solid rgba(120, 140, 170, 0.35);}')
        inner = QVBoxLayout(contents)
        inner.setContentsMargins(12, 4, 0, 6)
        contents.setVisible(opened)

        def fold(on):
            contents.setVisible(on)
            header.setArrowType(Qt.ArrowType.DownArrow if on else Qt.ArrowType.RightArrow)

        header.toggled.connect(fold)
        layout.addWidget(header)
        layout.addWidget(contents)
        inner.header = header
        return inner

    def changed(self, *args):
        """A setting of the block changed — the model rebuilt after a short pause (live panel only)."""
        if self.live:
            self.rebuild_timer.start()

    def docked(self):
        tool = getattr(self.owner, 'crystal_tool', None)
        return tool is not None and tool.side_dialog() is self

    def rebuild(self):
        """The block built again with the settings shown — only while this window is the panel beside the model."""
        if self.live and self.docked() and not self.isHidden():
            self.build()

    def done(self, result):
        self.rebuild_timer.stop()
        self.live = False
        super().done(result)

    @staticmethod
    def fit_width(body):
        """Nothing of the body asks for more
        width than the panel has — the number boxes shrink to their digits, the buttons may be squeezed (their words
        cut rather than the panel), the lists show fewer letters, the words of the labels wrap."""
        from PySide6.QtWidgets import QAbstractSpinBox, QComboBox, QLabel, QPushButton

        for box in body.findChildren(QAbstractSpinBox):
            narrow(box)
        for button in body.findChildren(QPushButton):
            button.setMinimumWidth(40)  # an explicit minimum: the row may squeeze it below its words, no further
        for combo in body.findChildren(QComboBox):
            combo.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            combo.setMinimumContentsLength(6)
            combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        for label in body.findChildren(QLabel):
            label.setWordWrap(True)

    def fit_screen(self, body):
        """As tall as the settings, but no taller than the screen (less a margin); wide enough for them."""
        from PySide6.QtGui import QGuiApplication

        screen = self.screen() or QGuiApplication.primaryScreen()
        room = screen.availableGeometry() if screen is not None else None
        hint = body.sizeHint()
        width = hint.width() + self.scroll.verticalScrollBar().sizeHint().width() + 40
        height = hint.height() + 90  # the buttons and the margins
        if room is not None:
            width = min(width, room.width() - 40)
            height = min(height, room.height() - 60)
        self.resize(max(width, 520), height)

    def n(self):
        return tuple(box.value() for box in self.counts)

    def explain_symbol(self):
        """What the Hermann–Mauguin symbol says, part by part (space_group_symbol.explain); the lines or None."""
        from PySide6.QtCore import Qt

        from azimuth import quill
        from modules.compass.chemistry import space_group_symbol as sg

        try:
            lines = sg.explain(self.data.space_group, self.symmetry.system if self.symmetry else '')
        except ValueError as exc:
            quill.warning(self, tr('Символ группы'), str(exc))
            return None
        box = QMessageBox(self)
        box.setWindowTitle(tr('Символ группы {}').format(self.data.space_group))
        box.setText('<br>'.join(lines))
        box.setTextFormat(Qt.TextFormat.RichText)
        self.symbol_box = box
        from azimuth.ui import open_window

        open_window(box)  # a window with its title, not a sheet
        return lines

    def chosen(self):
        """The crystal to build: with one part of its disorder when «Одна часть разупорядочения» is on."""
        return cr.main_part(self.data) if self.one_part.isChecked() else self.data

    def show_contacts(self, normalize=None, criteria=None):
        """The contacts of the crystal (crystal_contacts) in a table; «Показать сеть» puts the molecules
        they join on the model. The H atoms first moved to their neutron distances
        (crystal_hydrogens) unless normalize is False; the choice is kept for the next opening. Criteria —
        {'tolerance', 'hb_angle', 'hole_angle'} of the search (as «Define Contacts» of Mercury), kept the same way."""
        from modules.compass.chemistry import crystal_hydrogens

        if normalize is not None:
            self.normalize_h = bool(normalize)
        if criteria is not None:
            self.contact_criteria = dict(criteria)
        normalize = getattr(self, 'normalize_h', True)
        criteria = self.criteria()
        # the panel of the contacts found before comes back as it was (its rows, its choice, its lit
        # «Показать сеть»), unless the crystal, its part, the H positions or the criteria changed
        key = (id(self.data), self.one_part.isChecked(), normalize, tuple(sorted(criteria.items())))
        kept = getattr(self, 'contacts_window', None)
        if alive(kept) and getattr(kept, 'key', None) == key:
            self.owner.crystal_tool.contacts_window = kept
            self.owner.crystal_tool.dock(kept)
            kept.sync_network()
            return kept
        if alive(kept) and not kept.isVisible():
            kept.deleteLater()
        data, moved = self.chosen(), 0
        if normalize:
            data, moved = crystal_hydrogens.normalized(data)
        try:
            found = cc.contacts(data, **criteria)
        except ValueError as exc:
            self.owner.crystal_tool.w.error(exc)
            return None
        window = ContactsWindow(self, data, found, moved if normalize else None)
        window.key = key
        self.contacts_window = window
        self.owner.crystal_tool.contacts_window = window  # a click on a bond of the model chooses its row
        self.owner.crystal_tool.dock(window)  # beside the model, not over it
        return window

    def criteria(self):
        """The criteria of the contacts — those chosen in the «Контакты» window, else the defaults."""
        from modules.spectrum.analysis import contacts as mc

        chosen = getattr(self, 'contact_criteria', None) or {}
        return {'tolerance': chosen.get('tolerance', cc.TOLERANCE), 'hb_angle': chosen.get('hb_angle', mc.HB_ANGLE),
                'hole_angle': chosen.get('hole_angle', mc.HOLE_ANGLE)}

    def show_qe(self):
        """The periodic calculation of the cell in Quantum ESPRESSO (qe_window.py)."""
        from modules.compass.actions.qe_window import QeWindow

        window = QeWindow(self.owner, self.chosen(), self.windowTitle().replace(tr('Кристалл · '), '') or 'CIF')
        self.qe_window = window
        window.show()
        return window

    def show_powder(self):
        """The powder X-ray pattern of the crystal (powder.py) in a window of its own."""
        from modules.compass.actions.powder_window import PowderWindow

        window = PowderWindow(self, self.chosen())
        self.powder_window = window
        window.show()
        return window

    def ranges(self):
        """((x₁, y₁, z₁), (x₂, y₂, z₂)) of «Диапазон координат»."""
        return tuple(p[0].value() for p in self.range_boxes), tuple(p[1].value() for p in self.range_boxes)

    def build(self):
        """The block of the settings on the model; the panel beside the model stays open (it is closed by
        «Закрыть»), a window that is not the panel (built at the opening of a file) is closed as before."""
        self.rebuild_timer.stop()
        if self.by_range.isChecked():
            lo, hi = self.ranges()
            built = self.owner.crystal_tool.build_range(self.chosen(), lo, hi, self.whole.isChecked())
        else:
            built = self.owner.crystal_tool.build_crystal(self.chosen(), self.n(), self.faces.isChecked(),
                                                          self.whole.isChecked())
        if built and not self.docked():
            self.accept()
        return bool(built)

    def build_surface(self):
        hkl = tuple(s.value() for s in self.miller)
        n = (self.plane[0].value(), self.plane[1].value())
        self.rebuild_timer.stop()
        built = self.owner.crystal_tool.build_surface(self.chosen(), hkl, self.layers.value(), self.vacuum.value(), n)
        if built and not self.docked():
            self.accept()
        return bool(built)
