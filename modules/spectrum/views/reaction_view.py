"""Spectrum: the window «Диаграмма реакции». Numbers: modules/spectrum/analysis/reaction.py.

HEADER
    Left: the stages of the reaction and their species (results of calculations or numbers typed in), added,
    renamed (double click), moved and removed. Right: what to show (ΔE, ΔE₀, ΔH, ΔG), the unit, T, P, quasi-RRHO,
    the standard state 1 mol/L, the reference stage; the diagram — a level for every stage, dashed lines between
    them, transition states in their own colour with ‡, the barriers as arrows; under it the barriers, the energy of
    reaction and the warnings of reaction.profile. Export: PNG, SVG (the picture), CSV (the table), the table on
    the clipboard; the diagram itself as .json (results by their paths).
    Wilkinson convention, sections 1-8 (theory and error analysis: reaction.py §1, §8).

§2 ALGORITHM
    Every change of the stages or settings calls refresh(): reaction.profile(...) and a repaint; a ValueError is
    shown instead of the diagram. DiagramView.paint(painter, rect): y from the range of the shown values (10 %
    margin, nice ticks), x — equal slots, the level from 18 % to 82 % of a slot.
§3 APPLICATIONS
    modules/spectrum/workspace.py: reaction_diagram(), add_result_to_reaction().
§4 SPECIFICATION
    ReactionWindow(parent=None, read=reaction.read_species): .stages (list of reaction.Stage), add_files(paths,
    stage=None), add_species(species, stage=None), add_typed(...), move(k, step), remove(k, j=None), rename(k,
    label), refresh() -> Profile | None, save_picture(path), save_table(path), save_diagram(path), open_diagram(path).
§6 IMPLEMENTATION NOTES
    Colours come from the widget palette (base, text, mid), so the picture follows the light and dark themes;
    the transition states: #c0392b (light) / #ff8a7a (dark).
§7 TEST CASES
    tests/test_gui.py::test_reaction_diagram_window.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, QSize, Qt, QTimer
from PySide6.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.spectrum.analysis import reaction
from azimuth.i18n import tr
from azimuth import quill  # the messages with Quill

RESULT_FILTER = 'ORCA, Gaussian, xtb, Psi4, NWChem, Q-Chem, GAMESS (*.out *.log *.nwout *.qcout *.gamout);;Все файлы (*)'
SYMBOL = {'E': 'ΔE', 'E0': 'ΔE₀', 'H': 'ΔH', 'G': 'ΔG'}
NAMES = {
    'E': 'ΔE — электронная энергия',
    'E0': 'ΔE₀ — с нулевыми колебаниями',
    'H': 'ΔH — энтальпия',
    'G': 'ΔG — энергия Гиббса',
}
UNIT_NAMES = {'kcal': 'ккал/моль', 'kj': 'кДж/моль', 'ev': 'эВ'}


def flags(*items):
    """Alignment and text flags of different Qt enums as one int for QPainter.drawText."""
    out = 0
    for item in items:
        out |= int(getattr(item, 'value', item))
    return out


def nice_step(span, ticks=6):
    """A round step (1, 2, 2.5, 5 × 10ⁿ) giving about `ticks` divisions of span."""
    if span <= 0:
        return 1.0
    raw = span / ticks
    power = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
        if m * power >= raw:
            return m * power
    return 10 * power


class DiagramView(QWidget):
    LEFT, RIGHT, TOP, BOTTOM = 70, 24, 34, 58

    def __init__(self):
        super().__init__()
        self.result = None
        self.message = tr('Добавьте стадии: «Стадии из файлов…» или «Ввести вручную…»')
        self.setMinimumSize(420, 300)

    def set_result(self, result, message=''):
        self.result, self.message = result, message
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        self.paint(p, QRectF(self.rect()))
        p.end()

    def colours(self):
        pal = self.palette()
        base, text = pal.base().color(), pal.text().color()
        dark = base.lightness() < 128
        return base, text, QColor('#ff8a7a' if dark else '#c0392b'), QColor(text.red(), text.green(), text.blue(), 70)

    def paint(self, p, rect):
        base, ink, accent, faint = self.colours()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(rect, base)
        r = self.result
        shown = [] if r is None else [(k, v) for k, v in enumerate(r.values) if v is not None]
        if not shown:
            p.setPen(ink)
            p.drawText(rect.adjusted(20, 20, -20, -20), flags(Qt.AlignmentFlag.AlignCenter, Qt.TextFlag.TextWordWrap),
                       self.message or tr('Нечего показать'))
            return
        left, top = rect.left() + self.LEFT, rect.top() + self.TOP
        width = max(10.0, rect.width() - self.LEFT - self.RIGHT)
        height = max(10.0, rect.height() - self.TOP - self.BOTTOM)
        lo, hi = min(v for _, v in shown), max(v for _, v in shown)
        if hi - lo < 1e-9:
            lo, hi = lo - 1.0, hi + 1.0
        pad = (hi - lo) * 0.12
        lo, hi = lo - pad, hi + pad

        def y(v):
            return top + (hi - v) / (hi - lo) * height

        n = len(r.values)
        slot = width / n

        def bar(k):
            return left + slot * (k + 0.18), left + slot * (k + 0.82)

        # axis and ticks
        font = QFont(p.font())
        font.setPixelSize(12)
        p.setFont(font)
        p.setPen(QPen(faint, 1))
        step = nice_step(hi - lo)
        tick = math.ceil(lo / step) * step
        while tick <= hi + 1e-9:
            yy = y(tick)
            p.drawLine(QPointF(left - 4, yy), QPointF(left + width, yy))
            p.save()
            p.setPen(ink)
            p.drawText(QRectF(rect.left(), yy - 9, self.LEFT - 10, 18),
                       flags(Qt.AlignmentFlag.AlignRight, Qt.AlignmentFlag.AlignVCenter), f'{tick:g}')
            p.restore()
            tick += step
        p.setPen(QPen(ink, 1))
        p.drawLine(QPointF(left, top), QPointF(left, top + height))
        p.save()
        p.translate(rect.left() + 14, top + height / 2)
        p.rotate(-90)
        p.drawText(QRectF(-height / 2, -10, height, 20), Qt.AlignmentFlag.AlignCenter,
                   f'{SYMBOL[r.quantity]}, {tr(UNIT_NAMES[r.unit])}')
        p.restore()
        # connectors
        p.setPen(QPen(faint, 1.4, Qt.PenStyle.DashLine))
        previous = None
        for k, v in shown:
            if previous is not None and previous[0] == k - 1:
                p.drawLine(QPointF(bar(previous[0])[1], y(previous[1])), QPointF(bar(k)[0], y(v)))
            previous = (k, v)
        # levels, values, labels
        bold = QFont(font)
        bold.setBold(True)
        for k, v in shown:
            x0, x1 = bar(k)
            colour = accent if r.kinds[k] == 'ts' else ink
            p.setPen(QPen(colour, 3.2 if k != r.reference else 4.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
            p.drawLine(QPointF(x0, y(v)), QPointF(x1, y(v)))
            p.setFont(bold)
            p.setPen(colour)
            text = ('‡ ' if r.kinds[k] == 'ts' else '') + (f'{v:+.1f}' if abs(v) >= 0.05 else '0.0')
            p.drawText(QRectF(x0 - 10, y(v) - 22, x1 - x0 + 20, 18), Qt.AlignmentFlag.AlignCenter, text)
        p.setFont(font)
        p.setPen(ink)
        for k, label in enumerate(r.labels):
            x0, x1 = left + slot * k + 2, left + slot * (k + 1) - 2
            p.drawText(QRectF(x0, top + height + 8, x1 - x0, self.BOTTOM - 10),
                       flags(Qt.AlignmentFlag.AlignHCenter, Qt.AlignmentFlag.AlignTop, Qt.TextFlag.TextWordWrap), label)
        # barriers: a dotted line from the start level, an arrow up to the TS
        for b in r.barriers:
            if b.start is None or b.forward is None:
                continue
            v0, v1 = r.values[b.start], r.values[b.ts]
            x = sum(bar(b.ts)) / 2
            p.setPen(QPen(faint, 1, Qt.PenStyle.DotLine))
            p.drawLine(QPointF(bar(b.start)[1], y(v0)), QPointF(x, y(v0)))
            p.setPen(QPen(accent, 1.4))
            y0, y1 = y(v0), y(v1) + 4 if v1 > v0 else y(v1) - 4
            p.drawLine(QPointF(x, y0), QPointF(x, y1))
            head = QPainterPath()
            sign = -1 if v1 > v0 else 1
            head.moveTo(x, y1)
            head.lineTo(x - 4, y1 - sign * 7)
            head.lineTo(x + 4, y1 - sign * 7)
            head.closeSubpath()
            p.fillPath(head, QBrush(accent))
            p.drawText(QRectF(x + 6, (y0 + y1) / 2 - 9, slot * 0.5, 18),
                       flags(Qt.AlignmentFlag.AlignLeft, Qt.AlignmentFlag.AlignVCenter),
                       f'{SYMBOL[r.quantity]}‡ {b.forward:.1f}')


class TypedDialog(QDialog):
    """Type in a species: name, E and (if known) ZPE, H − E, G − E in hartree, the formula and the charge."""

    def __init__(self, parent=None, stage=None):
        super().__init__(parent)
        self.setWindowTitle(tr('Ввести вещество вручную'))
        form = QFormLayout(self)
        self.name = QLineEdit()
        self.energy = QLineEdit()
        self.zpe, self.enthalpy, self.gibbs = QLineEdit(), QLineEdit(), QLineEdit()
        self.formula = QLineEdit()
        self.charge = QLineEdit()
        for widget, hint in ((self.energy, '-76.4089'), (self.zpe, '0.0213'), (self.enthalpy, '0.0251'),
                             (self.gibbs, '0.0037'), (self.formula, 'H2O'), (self.charge, '0')):
            widget.setPlaceholderText(hint)
        form.addRow(tr('Название:'), self.name)
        form.addRow(tr('E, хартри:'), self.energy)
        form.addRow(tr('ZPE, хартри (если есть):'), self.zpe)
        form.addRow(tr('H − E, хартри (если есть):'), self.enthalpy)
        form.addRow(tr('G − E, хартри (если есть):'), self.gibbs)
        form.addRow(tr('Формула (для проверки атомов):'), self.formula)
        form.addRow(tr('Заряд:'), self.charge)
        self.ts = QCheckBox(tr('Переходное состояние'))
        form.addRow(self.ts)
        self.into = QCheckBox(tr('В выбранную стадию: ') + (stage or ''))
        self.into.setVisible(stage is not None)
        form.addRow(self.into)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    @staticmethod
    def number(text, name):
        text = text.strip().replace(',', '.').replace('−', '-')
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            raise ValueError(tr(f'Не число: {name}')) from None

    def species(self):
        charge = self.charge.text().strip().replace('−', '-')
        try:
            charge = int(charge) if charge else None
        except ValueError:
            raise ValueError(tr('Заряд — целое число.')) from None
        return reaction.typed_species(
            self.name.text(), self.number(self.energy.text(), 'E'), self.number(self.zpe.text(), 'ZPE'),
            self.number(self.enthalpy.text(), 'H − E'), self.number(self.gibbs.text(), 'G − E'),
            self.formula.text(), charge, self.ts.isChecked(),
        )


class ReactionWindow(QWidget):
    def __init__(self, parent=None, read=reaction.read_species):
        super().__init__(parent, Qt.WindowType.Window)
        self.read = read
        self.stages = []
        self.result = None
        self.setWindowTitle(tr('Диаграмма реакции'))
        self.resize(1100, 640)
        # in the style of the program — its background, two cards (stages, diagram), margins as the other
        # windows (was a bare splitter on the system background)
        from azimuth.ui import card

        self.setObjectName('workspace')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        split = QSplitter(Qt.Orientation.Horizontal, self)
        split.setHandleWidth(16)
        split.setChildrenCollapsible(False)
        outer = QHBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.addWidget(split)
        # left: the stages
        left, column = card(tr('Стадии'))
        hint = QLabel(tr('Стадии по порядку реакции; в стадии может быть несколько веществ (A + B). Двойной щелчок — переименовать.'))
        hint.setWordWrap(True)
        hint.setObjectName('subtitle')
        column.addWidget(hint)
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels([tr('Стадия / вещество'), tr('E, хартри')])
        self.tree.header().setStretchLastSection(False)  # the name takes the room («Стадия / веще» was cut)
        self.tree.header().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.tree.header().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.tree.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.tree.itemChanged.connect(self._renamed)
        self.tree.itemSelectionChanged.connect(self._selection)
        column.addWidget(self.tree, 1)
        grid = QVBoxLayout()
        row1, row2, row3 = QHBoxLayout(), QHBoxLayout(), QHBoxLayout()
        self.new_button = QPushButton(tr('Стадии из файлов…'))
        self.new_button.setToolTip(tr('Каждый выбранный файл — своя стадия, по порядку имён (реагенты, ПС, продукты …)'))
        self.new_button.clicked.connect(lambda: self.choose_files(None))
        self.into_button = QPushButton(tr('Добавить в стадию…'))
        self.into_button.setToolTip(tr('Ещё одно вещество в выбранную стадию (например, B в «A + B»)'))
        self.into_button.clicked.connect(lambda: self.choose_files(self.current_stage()))
        self.typed_button = QPushButton(tr('Ввести вручную…'))
        self.typed_button.clicked.connect(self.type_in)
        from azimuth.icons import iconify  # the arrows of the order — icons only

        self.up_button = iconify(QPushButton(), 'chevron-up', tr('Стадию выше'))
        self.up_button.clicked.connect(lambda: self.move(self.current_stage(), -1))
        self.down_button = iconify(QPushButton(), 'chevron-down', tr('Стадию ниже'))
        self.down_button.clicked.connect(lambda: self.move(self.current_stage(), 1))
        self.remove_button = QPushButton(tr('Убрать'))
        self.remove_button.clicked.connect(self.remove_selected)
        for row, widgets in ((row1, (self.new_button, self.into_button)), (row2, (self.typed_button,)),
                             (row3, (self.up_button, self.down_button, self.remove_button))):
            for w in widgets:
                row.addWidget(w)
            grid.addLayout(row)
        column.addLayout(grid)
        split.addWidget(left)
        # right: settings, the diagram, the summary
        right, side = card(tr('Диаграмма'))
        controls = QHBoxLayout()
        self.quantity = QComboBox()
        for key in reaction.QUANTITIES:
            self.quantity.addItem(tr(NAMES[key]), key)
        self.unit = QComboBox()
        for key in reaction.UNITS:
            self.unit.addItem(tr(UNIT_NAMES[key]), key)
        from azimuth import defaults

        self.unit.setCurrentIndex(max(0, self.unit.findData(defaults.get('energy_unit'))))  # «Настройки»
        self.temperature = QDoubleSpinBox()
        self.temperature.setRange(1.0, 5000.0)
        self.temperature.setDecimals(2)
        self.temperature.setValue(298.15)
        self.temperature.setSuffix(' K')
        self.pressure = QDoubleSpinBox()
        self.pressure.setRange(0.001, 1000.0)
        self.pressure.setDecimals(3)
        self.pressure.setValue(1.0)
        self.pressure.setSuffix(tr(' атм'))
        self.reference = QComboBox()
        self.reference.setToolTip(tr('Стадия, от которой отсчитываются энергии'))
        for widget in (self.quantity, self.unit, self.reference):
            widget.currentIndexChanged.connect(self.refresh)
        for widget in (self.temperature, self.pressure):
            widget.valueChanged.connect(self.refresh)
        controls.addWidget(self.quantity)
        controls.addWidget(self.unit)
        controls.addWidget(QLabel(tr('T:')))
        controls.addWidget(self.temperature)
        controls.addWidget(QLabel(tr('P:')))
        controls.addWidget(self.pressure)
        controls.addWidget(QLabel(tr('от:')))
        controls.addWidget(self.reference, 1)
        side.addLayout(controls)
        options = QHBoxLayout()
        self.qrrho = QCheckBox(tr('Квази-RRHO (Гримме) для мод ниже 100 см⁻¹'))
        self.molar = QCheckBox(tr('Стандартное состояние 1 моль/л (раствор)'))
        self.molar.setToolTip(tr('К G каждого вещества добавляется RT·ln(RT·c°/P) — 1,89 ккал/моль при 298 K и 1 атм; важно, когда меняется число молекул'))
        for box in (self.qrrho, self.molar):
            box.toggled.connect(self.refresh)
            options.addWidget(box)
        options.addStretch()
        side.addLayout(options)
        self.view = DiagramView()
        side.addWidget(self.view, 1)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        side.addWidget(self.summary)
        self.notes = QLabel()
        self.notes.setWordWrap(True)
        self.notes.setObjectName('notice')
        side.addWidget(self.notes)
        files = QHBoxLayout()
        self.open_button = QPushButton(tr('Открыть диаграмму…'))
        self.open_button.clicked.connect(self.choose_open)
        self.save_button = QPushButton(tr('Сохранить диаграмму…'))
        self.save_button.clicked.connect(self.choose_save)
        self.picture_button = QPushButton(tr('Картинка или таблица…'))
        self.picture_button.setToolTip(tr('PNG или SVG — рисунок, CSV — таблица'))
        self.picture_button.clicked.connect(self.choose_export)
        self.copy_button = QPushButton(tr('Копировать таблицу'))
        self.copy_button.clicked.connect(self.copy)
        self.rates_button = QPushButton(tr('Копировать k(T)'))
        self.rates_button.setToolTip(tr('Константы скорости по Эйрингу от 200 до 600 К (и при выбранной T) для ΔG‡ '
                                        'каждого барьера — таблицей для отчёта'))
        self.rates_button.setEnabled(False)
        self.rates_button.clicked.connect(self.copy_rates)
        for b in (self.open_button, self.save_button):
            files.addWidget(b)
        files.addStretch()
        for b in (self.picture_button, self.copy_button, self.rates_button):
            files.addWidget(b)
        side.addLayout(files)
        split.addWidget(right)
        split.setSizes([360, 740])
        self._fill()

    # -- settings --------------------------------------------------------------------------------------
    def settings(self):
        return {
            'quantity': self.quantity.currentData(), 'unit': self.unit.currentData(),
            'temperature': self.temperature.value(), 'pressure_atm': self.pressure.value(),
            'qrrho': self.qrrho.isChecked(), 'molar': self.molar.isChecked(),
            'reference': max(0, self.reference.currentIndex()),
        }

    def apply_settings(self, s):
        widgets = (self.quantity, self.unit, self.temperature, self.pressure, self.qrrho, self.molar)
        for w in widgets:
            w.blockSignals(True)
        try:
            for combo, key in ((self.quantity, 'quantity'), (self.unit, 'unit')):
                i = combo.findData(s.get(key))
                if i >= 0:
                    combo.setCurrentIndex(i)
            for spin, key in ((self.temperature, 'temperature'), (self.pressure, 'pressure_atm')):
                if isinstance(s.get(key), (int, float)):
                    spin.setValue(float(s[key]))
            self.qrrho.setChecked(bool(s.get('qrrho')))
            self.molar.setChecked(bool(s.get('molar')))
        finally:
            for w in widgets:
                w.blockSignals(False)

    # -- stages ------------------------------------------------------------------------------------------
    def current_stage(self):
        item = self.tree.currentItem()
        if item is None:
            return None
        top = item if item.parent() is None else item.parent()
        return self.tree.indexOfTopLevelItem(top)

    def add_species(self, species, stage=None):
        if stage is None or not 0 <= stage < len(self.stages):
            self.stages.append(reaction.Stage(species.label, (species,)))
            stage = len(self.stages) - 1
        else:
            old = self.stages[stage]
            labels = [s.label for s in old.species] + [species.label]
            label = old.label if old.label != ' + '.join(labels[:-1]) else ' + '.join(labels)
            self.stages[stage] = reaction.Stage(label, old.species + (species,))
        self._fill(stage)
        return stage

    def set_stages(self, stages, quantity=None):
        """The stages given in place of those of the window (the reaction of a project, «ΔG реакции…»),
        the quantity shown chosen ('E', 'E0', 'H', 'G')."""
        self.stages = list(stages)
        if quantity is not None:
            index = self.quantity.findData(quantity)
            if index >= 0:
                self.quantity.setCurrentIndex(index)
        self._fill(0 if self.stages else None)
        return self.stages

    def add_files(self, paths, stage=None):
        """Read the results: each into a stage of its own (stage None), or all into the given stage.
        Returns the problems (texts) of the files that could not be read."""
        problems = []
        for path in paths:
            try:
                species = self.read(str(path))
            except ValueError as exc:
                problems.append(f'{Path(path).name}: {exc}')
                continue
            self.add_species(species, stage)
        return problems

    def add_typed(self, species, stage=None):
        return self.add_species(species, stage)

    def choose_files(self, stage):
        paths, _ = QFileDialog.getOpenFileNames(self, tr('Результаты расчётов для стадии'), str(Path.home()), tr(RESULT_FILTER))
        if paths:
            problems = self.add_files(sorted(paths) if stage is None else paths, stage)
            if problems:
                quill.warning(self, tr('Не все файлы прочитаны'), '\n'.join(problems), 'file-unreadable')

    def type_in(self):
        k = self.current_stage()
        dialog = TypedDialog(self, None if k is None else self.stages[k].label)
        while dialog.exec() == QDialog.DialogCode.Accepted:
            try:
                self.add_typed(dialog.species(), k if dialog.into.isChecked() else None)
                return
            except ValueError as exc:
                quill.warning(self, tr('Не удалось выполнить действие'), str(exc))

    def move(self, k, step):
        if k is None or not 0 <= k + step < len(self.stages):
            return
        self.stages[k], self.stages[k + step] = self.stages[k + step], self.stages[k]
        self._fill(k + step)

    def remove(self, k, j=None):
        if k is None or not 0 <= k < len(self.stages):
            return
        if j is None or len(self.stages[k].species) <= 1:
            del self.stages[k]
            self._fill(min(k, len(self.stages) - 1))
        else:
            old = self.stages[k]
            self.stages[k] = reaction.Stage(old.label, old.species[:j] + old.species[j + 1:])
            self._fill(k)

    def remove_selected(self):
        item = self.tree.currentItem()
        if item is None:
            return
        if item.parent() is None:
            self.remove(self.tree.indexOfTopLevelItem(item))
        else:
            self.remove(self.tree.indexOfTopLevelItem(item.parent()), item.parent().indexOfChild(item))

    def rename(self, k, label):
        label = label.strip()
        if 0 <= k < len(self.stages) and label:
            self.stages[k] = reaction.Stage(label, self.stages[k].species)
            self._fill(k)

    def _renamed(self, item, column):
        if column == 0 and item.parent() is None:
            k = self.tree.indexOfTopLevelItem(item)
            if 0 <= k < len(self.stages) and item.text(0).strip() and item.text(0) != self.stages[k].label:
                text = item.text(0)
                QTimer.singleShot(0, lambda: self.rename(k, text))  # not while the editor still holds the item

    def _selection(self):
        k = self.current_stage()
        for b in (self.into_button, self.up_button, self.down_button, self.remove_button):
            b.setEnabled(k is not None)

    def _fill(self, select=None):
        self.tree.blockSignals(True)
        self.tree.clear()
        for k, stage in enumerate(self.stages):
            top = QTreeWidgetItem([stage.label, '‡' if stage.kind == 'ts' else ''])
            top.setFlags(top.flags() | Qt.ItemFlag.ItemIsEditable)
            if stage.kind == 'ts':
                for column in (0, 1):
                    top.setToolTip(column, tr('Переходное состояние: одна мнимая частота'))
                    top.setForeground(column, QBrush(QColor('#c0392b')))
            for s in stage.species:
                child = QTreeWidgetItem([s.label + (f' · {s.formula}' if s.formula else ''), f'{s.energy:.6f}'])
                tip = [s.program or tr('введено вручную'), s.path] + list(s.notes)
                if s.level:
                    tip.append(tr('уровень: ') + s.level)
                if s.imaginary:
                    tip.append(tr('мнимых частот: ') + str(len(s.imaginary)))
                child.setToolTip(0, '\n'.join(t for t in tip if t))
                top.addChild(child)
            self.tree.addTopLevelItem(top)
            top.setExpanded(True)
        self.tree.resizeColumnToContents(1)
        self.tree.blockSignals(False)
        current = self.reference.currentIndex()
        self.reference.blockSignals(True)
        self.reference.clear()
        for stage in self.stages:
            self.reference.addItem(stage.label)
        self.reference.setCurrentIndex(min(max(current, 0), len(self.stages) - 1) if self.stages else -1)
        self.reference.blockSignals(False)
        if select is not None and 0 <= select < len(self.stages):
            self.tree.setCurrentItem(self.tree.topLevelItem(select))
        self._selection()
        self.refresh()

    # -- the diagram ---------------------------------------------------------------------------------------
    def refresh(self, *args):
        if hasattr(self, 'rates_button'):
            self.rates_button.setEnabled(False)  # enabled again for a G profile with barriers
        if not self.stages:
            self.result = None
            self.view.set_result(None, tr('Добавьте стадии: «Стадии из файлов…» или «Ввести вручную…»'))
            self.summary.setText('')
            self.notes.setText('')
            return None
        s = self.settings()
        try:
            self.result = reaction.profile(
                self.stages, s['quantity'], s['unit'], min(s['reference'], len(self.stages) - 1), s['temperature'],
                s['pressure_atm'] * reaction.ATM, s['qrrho'], s['molar'],
            )
        except ValueError as exc:
            self.result = None
            self.view.set_result(None, str(exc))
            self.summary.setText('')
            self.notes.setText('')
            return None
        r = self.result
        unit, sym = tr(UNIT_NAMES[r.unit]), SYMBOL[r.quantity]
        lines = []
        for b in r.barriers:
            name = r.labels[b.ts]
            parts = []
            if b.forward is not None:
                parts.append(tr(f'прямой барьер {sym}‡ = {b.forward:.1f} {unit} (от «{r.labels[b.start]}»)'))
            if b.reverse is not None:
                parts.append(tr(f'обратный {b.reverse:.1f} {unit} (от «{r.labels[b.end]}»)'))
            lines.append(f'‡ «{name}»: ' + '; '.join(parts) if parts else f'‡ «{name}»')
            for rate in reaction.barrier_rates(r, self.stages, s['temperature'], s['pressure_atm'] * reaction.ATM,
                                               s['molar']):
                if rate.ts != b.ts:
                    continue
                text = 'k ' + (tr('прямой') if rate.direction == 'forward' else tr('обратной')) + \
                    f' = {reaction.scientific(rate.k)} {tr(reaction.rate_unit(rate.order))}'
                if rate.half_life is not None:
                    text += ', t½ = ' + reaction.duration(rate.half_life)
                lines.append('    ' + text)
                tunnel = reaction.tunnelling(self.stages, rate, s['temperature'])
                if tunnel is not None and rate.direction == 'forward':  # κ is the same in both directions
                    nu, wigner, eckart = tunnel
                    lines.append('    ' + tr('туннельная поправка (ν‡ = {}i см⁻¹): κ = {} по Вигнеру').format(
                        f'{nu:.0f}', f'{wigner:.2f}') + ('' if eckart is None else tr(', {} по Эккарту').format(
                            reaction.scientific(eckart) if eckart >= 100 else f'{eckart:.2f}')))
        if r.reaction is not None:
            lines.append(tr(f'{sym} реакции («{r.labels[0]}» → «{r.labels[-1]}»): {r.reaction:+.1f} {unit}'))
        if s['quantity'] in ('H', 'G'):
            lines.append(tr(f'T = {s["temperature"]:.2f} K, P = {s["pressure_atm"]:g} атм') + (tr(', 1 моль/л') if s['molar'] else ''))
        if r.quantity == 'G' and r.barriers:
            lines.append(tr('k — по Эйрингу (теория переходного состояния, κ = 1, без туннелирования); с туннелированием '
                            'k умножается на κ — они в таблице «Копировать k(T)».'))
        self.rates_button.setEnabled(r.quantity == 'G' and bool(r.barriers))
        self.summary.setText('\n'.join(lines))
        self.notes.setText('\n'.join('⚠ ' + w for w in r.warnings))
        self.view.set_result(r)
        return r

    def table(self):
        if self.result is None:
            return [], []
        s = self.settings()
        header = [tr('Стадия'), tr('Вещество'), tr('Тип'), f'{self.result.quantity}, ' + tr('хартри'),
                  f'{SYMBOL[self.result.quantity]}, ' + tr(UNIT_NAMES[self.result.unit])]
        body = reaction.rows(self.result, self.stages, s['temperature'], s['pressure_atm'] * reaction.ATM, s['qrrho'], s['molar'])
        return header, body

    def rate_rows(self):
        """Header and rows of k(T): reaction.rate_table at 200–600 K and at the chosen T."""
        s = self.settings()
        temperatures = sorted(set(reaction.RATE_TEMPERATURES) | {round(s['temperature'], 2)})
        rows = reaction.rate_table_tunnelling(self.stages, temperatures, s['pressure_atm'] * reaction.ATM, s['qrrho'],
                                              s['molar'])
        header = [tr('T, K'), tr('Переходное состояние'), tr('От стадии'), tr('Направление'), 'n',
                  'ΔG‡, ' + tr('ккал/моль'), 'k', tr('Единица k'), 't½, ' + tr('с'), tr('κ (Вигнер)'), tr('κ (Эккарт)'),
                  tr('k·κ (Эккарт)')]
        body = [[f'{t:g}', ts, start, tr('прямое') if d == 'forward' else tr('обратное'), str(n), f'{g:.2f}',
                 f'{k:.4e}', tr(reaction.rate_unit(n)), '' if half is None else f'{half:.4e}',
                 '' if wigner is None else f'{wigner:.3f}', '' if eckart is None else f'{eckart:.4g}',
                 '' if eckart is None else f'{k * eckart:.4e}']
                for t, ts, start, d, n, g, k, half, wigner, eckart in rows]
        return header, body

    def copy_rates(self):
        try:
            header, body = self.rate_rows()
        except ValueError as exc:
            self.notes.setText('⚠ ' + str(exc))
            return
        QApplication.clipboard().setText('\n'.join('\t'.join(row) for row in [header, *body]))
        from azimuth.ui import copied

        copied(self, tr('константы скорости'), self.rates_button)

    def copy(self):
        header, body = self.table()
        QApplication.clipboard().setText('\n'.join('\t'.join(row) for row in [header, *body]))
        from azimuth.ui import copied

        copied(self, tr('таблица реакции'), self.copy_button)

    # -- files ---------------------------------------------------------------------------------------------
    def picture(self, scale=2.0):
        size = QSize(max(self.view.width(), 900), max(self.view.height(), 520))
        image = QImage(size * scale, QImage.Format.Format_ARGB32)
        image.setDevicePixelRatio(scale)
        painter = QPainter(image)
        self.view.paint(painter, QRectF(0, 0, size.width(), size.height()))
        painter.end()
        return image

    def save_picture(self, path):
        path = Path(path)
        if self.result is None:
            raise ValueError(tr('Нечего сохранять: диаграмма пуста.'))
        suffix = path.suffix.lower()
        if suffix == '.png':
            if not self.picture().save(str(path)):
                raise OSError(tr('Не удалось сохранить PNG.'))
        elif suffix == '.svg':
            from PySide6.QtSvg import QSvgGenerator

            size = QSize(max(self.view.width(), 900), max(self.view.height(), 520))
            device = QSvgGenerator()
            device.setFileName(str(path))
            device.setSize(size)
            device.setViewBox(QRectF(0, 0, size.width(), size.height()))
            device.setTitle(tr('Диаграмма реакции'))
            painter = QPainter(device)
            if not painter.isActive():
                raise OSError(tr('Не удалось создать SVG.'))
            self.view.paint(painter, QRectF(0, 0, size.width(), size.height()))
            painter.end()
        elif suffix == '.csv':
            self.save_table(path)
        else:
            raise ValueError(tr('Поддерживаются PNG, SVG и CSV.'))

    def save_table(self, path):
        header, body = self.table()
        if not header:
            raise ValueError(tr('Нечего сохранять: диаграмма пуста.'))
        from modules.spectrum.wavefunction import field_tables

        field_tables.write_csv(path, header, body)  # the style of «Таблицы CSV» (Russian Excel: «;» and «,»)

    def save_diagram(self, path):
        path = Path(path)
        data = reaction.save(self.stages, self.settings(), path.parent)
        path.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding='utf-8')

    def open_diagram(self, path):
        path = Path(path)
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc:
            raise ValueError(tr('Не удалось открыть диаграмму: ') + str(exc)) from exc
        stages, settings, problems = reaction.load(data, path.parent, self.read)
        self.stages = stages
        self.apply_settings(settings)
        self._fill(0 if stages else None)
        if isinstance(settings.get('reference'), int) and 0 <= settings['reference'] < len(stages):
            self.reference.setCurrentIndex(settings['reference'])
        return problems

    def choose_open(self):
        path, _ = QFileDialog.getOpenFileName(self, tr('Открыть диаграмму реакции'), str(Path.home()),
                                              tr('Диаграмма реакции (*.json);;Все файлы (*)'))
        if path:
            try:
                problems = self.open_diagram(path)
            except ValueError as exc:
                quill.warning(self, tr('Не удалось выполнить действие'), str(exc))
                return
            if problems:
                quill.warning(self, tr('Не все файлы прочитаны'), '\n'.join(problems), 'file-unreadable')

    def choose_save(self):
        path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить диаграмму реакции'), str(Path.home() / 'reaction.json'),
                                              tr('Диаграмма реакции (*.json)'))
        if path:
            try:
                self.save_diagram(path)
            except OSError as exc:
                quill.warning(self, tr('Не удалось выполнить действие'), str(exc))

    def choose_export(self):
        path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить картинку или таблицу'), str(Path.home() / 'reaction.png'),
                                              tr('PNG (*.png);;SVG (*.svg);;CSV (*.csv)'))
        if path:
            try:
                self.save_picture(path)
            except (OSError, ValueError) as exc:
                quill.warning(self, tr('Не удалось выполнить действие'), str(exc))
