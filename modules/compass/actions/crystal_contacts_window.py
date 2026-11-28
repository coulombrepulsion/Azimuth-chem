"""Compass: the «Контакты» window of a crystal — the short contacts and hydrogen bonds of the structure, their table
(HydrogenBondTable) and «Показать сеть». Opened from the «Кристалл» window (crystal_window.CrystalWindow).

Split off modules/compass/actions/crystal_actions.py (0.222.29).
"""

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDoubleSpinBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)
from modules.compass.chemistry import crystal as cr
from modules.compass.chemistry import crystal_contacts as cc
from azimuth.i18n import tr
from azimuth.ui import action_button, help_button


class ContactsWindow(QDialog):
    """The hydrogen bonds and short contacts of a crystal; the repeated ones by symmetry are one row."""

    def __init__(self, crystal_window, data, found, moved=None):
        super().__init__(crystal_window)
        self.crystal_window, self.data, self.found = crystal_window, data, found
        self.setWindowTitle(tr('Контакты · ') + (data.title or 'CIF'))
        layout = QVBoxLayout(self)
        # the H atoms of an X-ray structure at their neutron distances before the search
        self.normalize = QCheckBox(tr('Атомы H — на нейтронных расстояниях (C–H 1,083, N–H 1,009, O–H 0,983 Å)'))
        self.normalize.setChecked(moved is not None)
        self.normalize.setToolTip(tr('Рентген видит электроны, и атом H в файле стоит на 0,1 Å ближе к своему атому, '
                                     'чем на самом деле; расстояния H···A водородных связей тогда длиннее настоящих. '
                                     'Средние длины связей с H по нейтронографии — Allen, Bruno, 2010.'))
        self.normalize.toggled.connect(self.renormalize)
        layout.addWidget(self.normalize)
        self.moved = moved
        rows = cc.grouped(found, cr.unit_cell(data))
        rows_of_contacts = rows
        hydrogen = sum(r[5] for r in rows if r[0] == 'hydrogen')
        holes = sum(r[5] for r in rows if r[0] not in ('hydrogen', 'vdw'))
        info = QLabel(tr('Водородных связей: {}, галогенных и других σ-дырочных: {}, других контактов: {} (ближе суммы '
                         'ван-дер-ваальсовых радиусов + {} Å)').format(
            hydrogen, holes, sum(r[5] for r in rows) - hydrogen - holes, f'{crystal_window.criteria()["tolerance"]:.2f}')
            + ('' if not moved else tr('; атомов H передвинуто на нейтронные расстояния: {}').format(moved)))
        info.setWordWrap(True)
        layout.addWidget(info)
        # the criteria of the search (Mercury's «Define Contacts»): the margin over the sum of the van der
        # Waals radii and the least angles; «Найти заново» runs the search again with them
        criteria = crystal_window.criteria()
        row = QHBoxLayout()
        self.tolerance = QDoubleSpinBox()
        self.tolerance.setRange(-0.5, 1.0)
        self.tolerance.setSingleStep(0.05)
        self.tolerance.setDecimals(2)
        self.tolerance.setValue(criteria['tolerance'])
        self.tolerance.setPrefix(tr('Σ r(вдВ) + '))
        self.tolerance.setSuffix(' Å')
        self.tolerance.setToolTip(tr('Контакт — атомы ближе суммы ван-дер-ваальсовых радиусов плюс этот запас '
                                     '(отрицательный — только заметно более короткие контакты)'))
        self.hb_angle = QDoubleSpinBox()
        self.hb_angle.setRange(90.0, 180.0)
        self.hb_angle.setDecimals(0)
        self.hb_angle.setValue(criteria['hb_angle'])
        self.hb_angle.setPrefix('D–H···A ≥ ')
        self.hb_angle.setSuffix('°')
        self.hb_angle.setToolTip(tr('Наименьший угол водородной связи'))
        self.hole_angle = QDoubleSpinBox()
        self.hole_angle.setRange(90.0, 180.0)
        self.hole_angle.setDecimals(0)
        self.hole_angle.setValue(criteria['hole_angle'])
        self.hole_angle.setPrefix('R–E···Y ≥ ')
        self.hole_angle.setSuffix('°')
        self.hole_angle.setToolTip(tr('Наименьший угол галогенной, халькогенной, пниктогенной и тетрельной связи'))
        self.again = action_button(tr('Найти заново'), self.search_again, 'search')
        self.again.setToolTip(tr('Найти контакты заново с этими критериями'))
        defaults = action_button(tr('По умолчанию'), self.default_criteria, 'reset-defaults')
        defaults.setToolTip(tr('Σ r(вдВ) + 0,20 Å, D–H···A ≥ 120°, R–E···Y ≥ 150°'))
        for widget in (self.tolerance, self.hb_angle, self.hole_angle, self.again, defaults):
            row.addWidget(widget)
        row.addStretch(1)
        layout.addLayout(row)
        from modules.compass.chemistry import crystal_graphsets as gs

        try:  # the graph set of Etter of each kind of hydrogen bond (first level)
            self.graph_sets = gs.for_contacts(data, found)
        except ValueError:
            self.graph_sets = [''] * len(rows)
        # d/Σr — the normalised contact; X···X — θ2 and the type of a contact of two halogens
        first = cc.representatives(found, cr.unit_cell(data))
        self.table = QTableWidget(len(rows), 9)
        self.table.setHorizontalHeaderLabels(
            [tr('Тип'), tr('Атомы'), 'd, Å', tr('Σ r(вдВ), Å'), 'd/Σr', tr('Угол, °'), 'X···X', tr('Число'), tr('Граф-набор')])
        self.table.horizontalHeaderItem(4).setToolTip(tr('Нормированный контакт: расстояние, делённое на сумму '
                                                         'ван-дер-ваальсовых радиусов; меньше 1 — атомы ближе, чем допускают радиусы'))
        self.table.horizontalHeaderItem(5).setToolTip(tr('D–H···A для водородной связи, R–E···Y (θ₁) для галогенной, '
                                                         'халькогенной, пниктогенной и тетрельной'))
        self.table.horizontalHeaderItem(6).setToolTip(tr(
            'Контакт двух галогенов R–X···X–R: θ₂ и тип. Тип I (θ₁ ≈ θ₂) — атомы касаются боками, это не галогенная '
            'связь; тип II (θ₁ ≈ 180°, θ₂ ≈ 90°) — σ-дырка одного направлена на пояс другого, галогенная связь'))
        self.table.horizontalHeaderItem(8).setToolTip(tr(
            'Узор водородных связей одного вида с их копиями по симметрии (Etter): D — одна связь между молекулами, '
            'S(n) — кольцо внутри молекулы, C(n) — бесконечная цепь, R(n) — кольцо из нескольких молекул; '
            'n — атомов в кольце или в звене цепи, верхний и нижний индексы — число акцепторов и водородов'))
        for k, (kind, text, d, total, angle, count) in enumerate(rows):
            c = first[k]
            pair = '' if not c.geometry else tr('θ₂ {}°, тип {}').format(f'{c.angle2:.1f}', c.geometry)
            values = [cc.name(kind), text, f'{d:.3f}', f'{total:.2f}', f'{d / total:.2f}' if total else '',
                      '' if angle is None else f'{angle:.1f}', pair, str(count),
                      self.graph_sets[k] if k < len(self.graph_sets) else '']
            for col, value in enumerate(values):
                self.table.setItem(k, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.itemSelectionChanged.connect(self.mark_chosen)  # the chosen rows are highlighted on the model
        layout.addWidget(self.table)
        self.row_contacts = cc.row_contacts(found, cr.unit_cell(data))  # the rows for «Показать сеть»
        # the second level — the patterns of two kinds of hydrogen bonds together
        try:
            self.second_level = gs.second_level(data, found)
        except ValueError:
            self.second_level = []
        self.pairs = QTableWidget(len(self.second_level), 3)
        self.pairs.setHorizontalHeaderLabels([tr('Первая связь'), tr('Вторая связь'), tr('Граф-набор второго уровня')])
        self.pairs.horizontalHeaderItem(2).setToolTip(tr(
            'Узор из связей двух видов вместе (Bernstein и др., 1995): кольцо R или цепь C, в которые входят связи '
            'обоих видов; для лестницы — и кольцо, и цепь. Конечные узоры второго уровня не называются'))
        for k, (i, j, text) in enumerate(self.second_level):
            for col, value in enumerate((rows[i][1], rows[j][1], text)):
                self.pairs.setItem(k, col, QTableWidgetItem(value))
        self.pairs.resizeColumnsToContents()
        self.pairs.setVisible(bool(self.second_level))
        layout.addWidget(self.pairs)
        # the planar rings of the molecules and their π–π stacking; C–H···π (crystal_rings)
        from modules.compass.chemistry import crystal_rings as rg

        try:
            self.rings, stacks = rg.stacking(data)
            _, near = rg.ch_pi(data)
        except ValueError:
            self.rings, stacks, near = (), (), ()
        self.stack_rows = rg.grouped(self.rings, stacks)
        self.ch_pi_rows = rg.ch_pi_grouped(data, self.rings, near) if near else []
        self.stacking_info = QLabel(tr('Плоских колец в ячейке: {}; π–π-стопок (Cg···Cg до {} Å, угол плоскостей до {}°): {}; '
                                       'C–H···π (H···Cg до {} Å): {}').format(
            len(self.rings), f'{rg.CG_LIMIT:.1f}', f'{rg.ANGLE_LIMIT:.0f}', sum(r[5] for r in self.stack_rows),
            f'{rg.CH_PI_LIMIT:.1f}', sum(r[5] for r in self.ch_pi_rows)))
        self.stacking_info.setWordWrap(True)
        layout.addWidget(self.stacking_info)
        rows = [('π–π',) + r for r in self.stack_rows] + [('C–H···π',) + r for r in self.ch_pi_rows]
        self.stacks = QTableWidget(len(rows), 7)
        self.stacks.setHorizontalHeaderLabels(
            [tr('Тип'), tr('Кольца'), 'd, Å', tr('Угол, °'), tr('До плоскости, Å'), tr('Сдвиг, Å'), tr('Число')])
        self.stacks.horizontalHeaderItem(2).setToolTip(tr('Cg···Cg для π–π, H···Cg для C–H···π'))
        self.stacks.horizontalHeaderItem(3).setToolTip(tr('Между плоскостями колец для π–π, C–H···Cg для C–H···π'))
        self.stacks.horizontalHeaderItem(4).setToolTip(tr('Расстояние от центроида первого кольца до плоскости второго'))
        self.stacks.horizontalHeaderItem(5).setToolTip(tr('Смещение колец вдоль плоскости: √(d² − d⊥²)'))
        for k, (kind, text, d, angle, perpendicular, offset, count) in enumerate(rows):
            for col, value in enumerate((kind, text, f'{d:.3f}', f'{angle:.1f}', f'{perpendicular:.3f}', f'{offset:.3f}',
                                         str(count))):
                self.stacks.setItem(k, col, QTableWidgetItem(value))
        self.stacks.resizeColumnsToContents()
        self.stacks.setVisible(bool(rows))
        layout.addWidget(self.stacks)
        buttons = QHBoxLayout()
        # the network of the hydrogen bonds, of the σ-hole bonds or of all the specific ones
        from modules.spectrum.analysis import contacts as mc

        present = [k for k in mc.ORDER if any(r[0] == k for r in rows_of_contacts)]
        self.network_kinds = QComboBox()
        if 'hydrogen' in present:
            self.network_kinds.addItem(tr('водородных связей'), ('hydrogen',))
        holes = tuple(k for k in present if k != 'hydrogen')
        if holes:
            self.network_kinds.addItem(tr('галогенных и других σ-дырочных связей'), holes)
        # the π–π stacks and the C–H···π of the second table
        stacking = tuple(k for k, rows_of_kind in (('pi', self.stack_rows), ('ch_pi', self.ch_pi_rows)) if rows_of_kind)
        if stacking:
            self.network_kinds.addItem(tr('π–π-стопок и C–H···π'), stacking)
        if len([x for x in ('hydrogen' in present, bool(holes), bool(stacking)) if x]) > 1:
            self.network_kinds.addItem(tr('всех специфических связей'), tuple(present) + stacking)
        present = present + list(stacking)
        self.network_button = QPushButton(tr('Показать сеть'))
        self.network_button.setToolTip(tr('Молекулы ячейки и соседние молекулы, связанные с ними выбранными связями'))
        self.network_button.setEnabled(bool(present))
        # a switch — lit while the network is on the model, pressed again it goes
        self.network_button.setCheckable(True)
        self.network_button.setStyleSheet('QPushButton:checked {background: #2a62b8; color: white; '
                                          'border: 1px solid #2a62b8; border-radius: 6px;}')
        self.network_button.clicked.connect(self.network_clicked)
        buttons.addWidget(self.network_button)
        buttons.addWidget(self.network_kinds)
        # 0.170.0 (Mercury's «expand contacts»): the network grown layer by layer; the rows picked — only their bonds
        self.layers = QSpinBox()
        self.layers.setRange(1, 6)
        self.layers.setValue(1)
        self.layers.setPrefix(tr('слоёв: '))
        self.layers.setToolTip(tr('Сколько раз наращивать сеть от добавленных молекул. Выделите строки таблицы, '
                                  'чтобы сеть строилась только по этим контактам'))
        buttons.addWidget(self.layers)
        self.network_kinds.setVisible(self.network_kinds.count() > 1)
        # the hydrogen bonds as a table of a paper, with the symmetry codes of the acceptors
        self.bonds = cc.hydrogen_bonds(data, found)
        self.paper_button = action_button(tr('Таблица для статьи…'), self.show_paper_table, 'table')
        self.paper_button.setToolTip(tr('Водородные связи: D–H, H···A, D···A, угол D–H···A и коды симметрии акцепторов'))
        self.paper_button.setEnabled(bool(self.bonds))
        buttons.addWidget(self.paper_button)
        buttons.addStretch(1)
        close = action_button(tr('Закрыть'), self.reject, 'close')
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def mark_chosen(self):
        """The contacts of the rows chosen drawn on the model and their atoms selected, where both atoms
        are on it; told when none is (the molecules of the cell only — «Показать сеть» puts the neighbours)."""
        chosen = self.chosen_contacts()
        if not chosen:
            return 0
        tool = self.crystal_window.owner.crystal_tool
        lines = tool.show_contacts_on_model(self.data, chosen, None if any(c.kind == 'vdw' for c in chosen)
                                            else {c.kind for c in chosen} or None, select=True)
        if not lines and any(c.kind == 'vdw' for c in chosen):
            lines = tool.show_contacts_on_model(self.data, chosen, {c.kind for c in chosen}, select=True)
        if not lines:
            tool.w.notify(tr('Этого контакта нет на модели: его второй атом — в соседней молекуле. «Показать сеть» '
                             'добавит соседей.'), 8000)
        return lines

    def renormalize(self, on):
        """The contacts again with the H atoms normalised or as in the file."""
        again = self.crystal_window.show_contacts(normalize=on)
        if again is not None and again is not self:
            self.close()
        return again

    def chosen_criteria(self):
        return {'tolerance': self.tolerance.value(), 'hb_angle': self.hb_angle.value(), 'hole_angle': self.hole_angle.value()}

    def search_again(self):
        """The contacts again with the criteria of the window."""
        again = self.crystal_window.show_contacts(criteria=self.chosen_criteria())
        if again is not None and again is not self:
            self.close()
        return again

    def default_criteria(self):
        from modules.spectrum.analysis import contacts as mc

        self.tolerance.setValue(cc.TOLERANCE)
        self.hb_angle.setValue(mc.HB_ANGLE)
        self.hole_angle.setValue(mc.HOLE_ANGLE)
        return self.search_again()

    def show_paper_table(self):
        window = HydrogenBondTable(self, self.bonds, self.data.title or 'CIF')
        self.paper_table = window
        window.show()
        return window

    def chosen_contacts(self):
        """The contacts of the rows selected in the table, or None when no row is selected."""
        rows = sorted({index.row() for index in self.table.selectedIndexes()})
        if not rows:
            return None
        return [c for r in rows if r < len(self.row_contacts) for c in self.row_contacts[r]]

    def show_network(self):
        kinds = self.network_kinds.currentData() or ('hydrogen',)
        # the panel stays open beside the network (it was closed with the window)
        built = self.crystal_window.owner.crystal_tool.build_network(self.data, kinds, self.crystal_window.criteria(),
                                                                    self.layers.value(), self.chosen_contacts())
        self.network_button.setChecked(bool(built))
        self.network_button.setToolTip(tr('Сеть на модели — нажмите ещё раз, чтобы убрать её') if built else
                                       tr('Молекулы ячейки и соседние молекулы, связанные с ними выбранными связями'))
        return built

    def hide_network(self):
        """The network taken off — the block of the «Кристалл» panel again, without the lines."""
        self.network_button.setChecked(False)
        self.network_button.setToolTip(tr('Молекулы ячейки и соседние молекулы, связанные с ними выбранными связями'))
        viewer = self.crystal_window.owner.viewer
        viewer.found_contacts = None
        built = self.crystal_window.build()
        viewer.update()
        return built

    def sync_network(self):
        """«Показать сеть» lit when the model shows the network (CrystalTool.network_on), as the panel comes back."""
        on = bool(getattr(self.crystal_window.owner.crystal_tool, 'network_on', False))
        self.network_button.setChecked(on)
        self.network_button.setToolTip(tr('Сеть на модели — нажмите ещё раз, чтобы убрать её') if on else
                                       tr('Молекулы ячейки и соседние молекулы, связанные с ними выбранными связями'))

    def network_clicked(self, on=None):
        on = self.network_button.isChecked() if on is None else on
        return self.show_network() if on else self.hide_network()


class HydrogenBondTable(QDialog):
    """The hydrogen bonds of a crystal as in a paper (Mercury, PLATON): D–H···A with the acceptor marked by
    the symmetry code (i, ii …), D–H, H···A, D···A in Å and the angle; the codes under the table. «Копировать» puts
    it on the clipboard with tabs (a table in a word processor), «Сохранить CSV…» writes a file."""

    def __init__(self, parent, bonds, title):
        super().__init__(parent)
        self.bonds = bonds
        self.setWindowTitle(tr('Водородные связи · ') + title)
        layout = QVBoxLayout(self)
        mark = cc.marks(bonds)
        self.table = QTableWidget(len(bonds), 6)
        self.table.setHorizontalHeaderLabels(['D–H···A', 'D–H, Å', 'H···A, Å', 'D···A, Å', 'D–H···A, °', tr('Код симметрии A')])
        for k, b in enumerate(bonds):
            name = f'{b.donor}–{b.hydrogen}···{b.acceptor}' + (f' ({mark[b.code]})' if b.code in mark else '')
            values = (name, f'{b.d_dh:.2f}', f'{b.d_ha:.2f}', f'{b.d_da:.3f}', f'{b.angle:.0f}',
                      b.code or 'x, y, z')
            for col, value in enumerate(values):
                self.table.setItem(k, col, QTableWidgetItem(value))
        self.table.resizeColumnsToContents()
        layout.addWidget(self.table)
        # the explanation behind «?» (help_button), not on the page
        note = tr('Донор D — в независимой части файла (x, y, z); код — операция, которая ставит акцептор A '
                  'из его положения в файле туда, где он принимает связь. «?» — атом не получен операциями файла.')
        buttons = QHBoxLayout()
        buttons.addWidget(help_button(note))
        copy = action_button(tr('Копировать'), self.copy, 'copy')
        copy.setToolTip(tr('Таблица с табуляциями — вставляется таблицей в текстовый редактор и в электронную таблицу'))
        buttons.addWidget(copy)
        buttons.addWidget(action_button(tr('Сохранить CSV…'), self.save_csv, 'save'))
        buttons.addStretch(1)
        buttons.addWidget(action_button(tr('Закрыть'), self.reject, 'close'))
        layout.addLayout(buttons)
        self.resize(720, 360)

    def text(self):
        from azimuth import i18n

        return cc.hydrogen_table(self.bonds, ',' if i18n.LANG == 'ru' else '.')

    def copy(self):
        from PySide6.QtWidgets import QApplication

        QApplication.clipboard().setText(self.text())
        from azimuth.ui import copied

        copied(self, tr('таблица водородных связей'), self.sender() if hasattr(self.sender(), 'setText') else None)
        return True

    def csv(self):
        import csv
        import io

        out = io.StringIO()
        writer = csv.writer(out)
        writer.writerow(['D', 'H', 'A', 'symmetry_A', 'D-H', 'H...A', 'D...A', 'D-H...A', 'count'])
        for b in self.bonds:
            writer.writerow([b.donor, b.hydrogen, b.acceptor, b.code or 'x, y, z', f'{b.d_dh:.4f}', f'{b.d_ha:.4f}',
                             f'{b.d_da:.4f}', f'{b.angle:.2f}', b.count])
        return out.getvalue()

    def save_csv(self, path=None):
        if path is None:
            from PySide6.QtWidgets import QFileDialog

            path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить таблицу водородных связей'), 'hbonds.csv', 'CSV (*.csv)')
            if not path:
                return False
        with open(path, 'w', encoding='utf-8', newline='') as handle:
            handle.write(self.csv())
        return True
