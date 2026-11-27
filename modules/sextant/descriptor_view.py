"""«Дескрипторы и logK»: the descriptors of a finished queue next to the constants of its records, one fitted against
another. The numbers: modules/spectrum/analysis/descriptors.py; this is the window.

§2 ALGORITHM
    DescriptorWindow(owner, queue, extra=None): the table of descriptors.table (sortable); two lists — the descriptor
    (x) and the constant (y) among descriptors.constant_columns; the constant first offered is the first column named
    logK…, the descriptor — «ΔE связывания» when the queue is a binding one, else the first number that is not y. The
    plot (ScatterPlot): the points, the line of descriptors.fit, the outliers ringed and named; the equation, n, r, R²,
    Q² (leave-one-out), RMSE under it. «Сохранить в «Анализ»» writes descriptors_table.csv and descriptors_fit.csv (the
    pairs, the predicted values and the residuals) into «Анализ» of the folder of the queue; «Картинка…» — a PNG of the
    plot.
§4 SPECIFICATION
    DescriptorWindow(owner, queue, extra=None); choose(x, y) -> Fit | None; save() -> [Path]; save_picture(path=None).
    ScatterPlot.set_points(xs, ys, names, fit, x_title, y_title).
§7 TESTS
    tests/test_gui.py::test_descriptor_window_fits_a_constant.
"""

from __future__ import annotations

import math
from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPalette, QPen
from PySide6.QtWidgets import (QComboBox, QDialog, QHBoxLayout, QHeaderView, QSplitter, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from modules.spectrum.analysis import descriptors

ACCENT = QColor('#2a62b8')
OUTLIER = QColor('#c0392b')


def nice_ticks(low, high, count=5):
    """Round numbers between low and high for the axes."""
    if not (math.isfinite(low) and math.isfinite(high)) or high <= low:
        return [low]
    raw = (high - low) / max(1, count)
    power = 10 ** math.floor(math.log10(raw))
    step = min((m * power for m in (1, 2, 2.5, 5, 10) if m * power >= raw), default=raw)
    first = math.ceil(low / step) * step
    ticks, value = [], first
    while value <= high + 1e-9 * step:
        ticks.append(round(value, 12))
        value += step
    return ticks


def short(value):
    if value is None:
        return ''
    if abs(value) >= 1e4 or (0 < abs(value) < 1e-3):
        return f'{value:.3e}'
    return f'{value:.4g}'


class ScatterPlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(320, 200)  # the window fits a laptop screen
        self.setMouseTracking(True)
        self.points, self.names, self.result = [], [], None
        self.x_title = self.y_title = ''

    def set_points(self, xs, ys, names, result, x_title, y_title):
        self.points = [(x, y) for x, y in zip(xs, ys)]
        self.names, self.result = list(names), result
        self.x_title, self.y_title = x_title, y_title
        self.update()

    def _frame(self):
        return QRectF(64, 18, max(10, self.width() - 84), max(10, self.height() - 64))

    def _ranges(self):
        xs = [x for x, _ in self.points] or [0.0, 1.0]
        ys = [y for _, y in self.points] or [0.0, 1.0]
        (x0, x1), (y0, y1) = (min(xs), max(xs)), (min(ys), max(ys))
        dx, dy = (x1 - x0) or abs(x0) or 1.0, (y1 - y0) or abs(y0) or 1.0
        return x0 - 0.08 * dx, x1 + 0.08 * dx, y0 - 0.08 * dy, y1 + 0.08 * dy

    def _map(self, x, y, frame, ranges):
        x0, x1, y0, y1 = ranges
        return QPointF(frame.left() + (x - x0) / (x1 - x0) * frame.width(),
                       frame.bottom() - (y - y0) / (y1 - y0) * frame.height())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().color(QPalette.ColorRole.WindowText)
        faint = QColor(ink)
        faint.setAlpha(40)
        frame, ranges = self._frame(), self._ranges()
        x0, x1, y0, y1 = ranges
        font = QFont(self.font())
        font.setPointSizeF(max(8.0, font.pointSizeF() - 1))
        p.setFont(font)
        for value in nice_ticks(x0, x1):
            at = self._map(value, y0, frame, ranges).x()
            p.setPen(QPen(faint, 1))
            p.drawLine(QPointF(at, frame.top()), QPointF(at, frame.bottom()))
            p.setPen(ink)
            p.drawText(QRectF(at - 40, frame.bottom() + 4, 80, 16), Qt.AlignmentFlag.AlignHCenter, short(value))
        for value in nice_ticks(y0, y1):
            at = self._map(x0, value, frame, ranges).y()
            p.setPen(QPen(faint, 1))
            p.drawLine(QPointF(frame.left(), at), QPointF(frame.right(), at))
            p.setPen(ink)
            p.drawText(QRectF(0, at - 8, frame.left() - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                       short(value))
        p.setPen(QPen(ink, 1.2))
        p.drawRect(frame)
        p.drawText(QRectF(frame.left(), frame.bottom() + 22, frame.width(), 18), Qt.AlignmentFlag.AlignHCenter, self.x_title)
        p.save()
        p.translate(14, frame.center().y())
        p.rotate(-90)
        p.drawText(QRectF(-frame.height() / 2, -9, frame.height(), 18), Qt.AlignmentFlag.AlignHCenter, self.y_title)
        p.restore()
        if not self.points:
            p.drawText(frame, Qt.AlignmentFlag.AlignCenter, tr('Нет пар значений'))
            return
        result = self.result
        if result is not None:
            p.setClipRect(frame)
            p.setPen(QPen(ACCENT, 1.6, Qt.PenStyle.DashLine))
            p.drawLine(self._map(x0, result.intercept + result.slope * x0, frame, ranges),
                       self._map(x1, result.intercept + result.slope * x1, frame, ranges))
            p.setClipping(False)
        outliers = set(result.outliers) if result is not None else set()
        for k, (x, y) in enumerate(self.points):
            at = self._map(x, y, frame, ranges)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(ACCENT)
            p.drawEllipse(at, 4.2, 4.2)
            if k in outliers:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.setPen(QPen(OUTLIER, 1.6))
                p.drawEllipse(at, 8, 8)
                p.drawText(at + QPointF(10, -6), self.names[k] if k < len(self.names) else '')

    def mouseMoveEvent(self, event):
        frame, ranges = self._frame(), self._ranges()
        best, where = None, 12.0
        for k, (x, y) in enumerate(self.points):
            d = (self._map(x, y, frame, ranges) - event.position()).manhattanLength()
            if d < where:
                best, where = k, d
        if best is None:
            self.setToolTip('')
            return
        x, y = self.points[best]
        name = self.names[best] if best < len(self.names) else ''
        self.setToolTip(f'{name}\n{self.x_title}: {short(x)}\n{self.y_title}: {short(y)}')


class DescriptorWindow(QDialog):
    def __init__(self, owner, queue, extra=None):
        from azimuth.ui import button, card, center_combo, label

        super().__init__(owner)
        self.owner, self.queue = owner, queue
        self.setWindowTitle(tr('Дескрипторы и logK'))
        self.setObjectName('workspace')
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.columns, self.rows = descriptors.table(queue, extra)
        self.numeric = descriptors.constant_columns(self.columns, self.rows)
        outer = QVBoxLayout(self)
        outer.setContentsMargins(16, 16, 16, 16)
        outer.setSpacing(12)
        frame, column = card(tr('Расчёты очереди и константы записей'))
        column.addWidget(label(tr(f'Очередь: {Path(queue.folder).name} · расчётов с результатом: {len(self.rows)}. '
                                  'Константы — поля SDF-записей (logK …); столбцы QTAIM появятся после «QTAIM для всех».'),
                               'subtitle'))
        self.table = QTableWidget(len(self.rows), len(self.columns))
        self.table.setHorizontalHeaderLabels(self.columns)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.verticalHeader().hide()
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        for i, row in enumerate(self.rows):
            for j, value in enumerate(row):
                item = QTableWidgetItem()
                found = descriptors.number(value) if j else None
                if found is not None:
                    item.setData(Qt.ItemDataRole.DisplayRole, float(f'{found:.6g}'))
                else:
                    item.setText(str(value))
                self.table.setItem(i, j, item)
        self.table.setSortingEnabled(True)
        self.table.setMinimumHeight(110)
        column.addWidget(self.table, 1)
        # the cards in a splitter, the lists and the labels shrinking, the window not taller or wider than the screen
        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        splitter.addWidget(frame)
        frame, column = card(tr('Корреляция'))
        choose = QHBoxLayout()
        self.x_box, self.y_box = center_combo(QComboBox()), center_combo(QComboBox())
        for box in (self.x_box, self.y_box):
            box.setSizeAdjustPolicy(QComboBox.SizeAdjustPolicy.AdjustToMinimumContentsLengthWithIcon)
            box.setMinimumContentsLength(8)
            for name in self.numeric:
                box.addItem(name, name)
        for text, box in ((tr('Дескриптор (x)'), self.x_box), (tr('Константа (y)'), self.y_box)):
            words = label(text, 'subtitle')
            words.setWordWrap(False)
            choose.addWidget(words)
            choose.addWidget(box, 1)
        self.choice_row = QWidget()
        self.choice_row.setLayout(choose)
        choose.setContentsMargins(0, 0, 0, 0)
        column.addWidget(self.choice_row)
        self.plot = ScatterPlot()
        column.addWidget(self.plot, 1)
        self.summary = label('', 'subtitle')
        self.summary.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        column.addWidget(self.summary)
        splitter.addWidget(frame)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        outer.addWidget(splitter, 1)
        # with fewer than two numbers of three values there is nothing to fit: the note alone, no empty plot
        fits = len(self.numeric) >= 2
        self.choice_row.setVisible(fits)
        self.plot.setVisible(fits)
        buttons = QHBoxLayout()
        self.save_button = button(tr('Сохранить в «Анализ»'), self.save)
        self.picture_button = button(tr('Сохранить рисунок…'), lambda: self.save_picture())
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.picture_button)
        buttons.addStretch(1)
        buttons.addWidget(button(tr('Закрыть'), self.accept))  # what closes is white
        outer.addLayout(buttons)
        y = next((c for c in self.numeric if 'logk' in c.lower()), self.numeric[-1] if self.numeric else None)
        x = next((c for c in self.numeric if c == tr('ΔE связывания, ккал/моль')), None) or next(
            (c for c in self.numeric if c != y), None)
        if x is not None:
            self.x_box.setCurrentIndex(self.x_box.findData(x))
        if y is not None:
            self.y_box.setCurrentIndex(self.y_box.findData(y))
        self.x_box.currentIndexChanged.connect(lambda *_: self.choose())
        self.y_box.currentIndexChanged.connect(lambda *_: self.choose())
        self.result = None
        self.choose()
        if not fits:
            self.summary.setText(tr('Сопоставлять не с чем: нужны хотя бы два числовых столбца с тремя значениями — '
                                    'константы (logK …) берутся из полей SDF-записей очереди.'))
            self.picture_button.setEnabled(False)
        width, height = 980, 760 if fits else 520
        screen = (owner.screen() if owner is not None else None) or self.screen()
        if screen is not None:
            room = screen.availableGeometry()
            width, height = min(width, room.width() - 40), min(height, room.height() - 60)
        self.resize(width, height)

    def values(self, name):
        k = self.columns.index(name)
        return [descriptors.number(row[k]) for row in self.rows]

    def pairs(self, x, y):
        xs, ys = self.values(x), self.values(y)
        return [(row[0], a, b) for row, a, b in zip(self.rows, xs, ys) if a is not None and b is not None]

    def choose(self, x=None, y=None):
        x = x or self.x_box.currentData()
        y = y or self.y_box.currentData()
        self.result = None
        if not x or not y:
            self.summary.setText(tr('Нужны хотя бы два числовых столбца с тремя значениями.'))
            self.plot.set_points([], [], [], None, x or '', y or '')
            return None
        pairs = self.pairs(x, y)
        names = [n for n, *_ in pairs]
        xs, ys = [a for _, a, _ in pairs], [b for *_, b in pairs]
        try:
            self.result = descriptors.fit(xs, ys)
        except ValueError as exc:
            self.summary.setText(str(exc))
            self.plot.set_points(xs, ys, names, None, x, y)
            return None
        f = self.result
        sign = '+' if f.slope >= 0 else '−'
        text = (f'{y} = {f.intercept:.4g} {sign} {abs(f.slope):.4g} · {x}   ·   n = {f.n}, r = {f.r:.3f}, '
                f'R² = {f.r2:.3f}, ' + (f'Q²(LOO) = {f.q2:.3f}, ' if f.q2 is not None else '') + f'RMSE = {f.rmse:.3g}')
        if f.outliers:
            text += '\n' + tr('Выбросы (|остаток| > 2·RMSE): ') + ', '.join(names[k] for k in f.outliers)
        self.summary.setText(text)
        self.plot.set_points(xs, ys, names, f, x, y)
        return f

    def save(self):
        from modules.spectrum.wavefunction import field_tables

        tables = {'table': (self.columns, [[descriptors.number(v) if j and descriptors.number(v) is not None else v
                                            for j, v in enumerate(row)] for row in self.rows])}
        x, y = self.x_box.currentData(), self.y_box.currentData()
        if self.result is not None and x and y:
            pairs = self.pairs(x, y)
            f = self.result
            rows = [[n, a, b, p, e, tr('выброс') if k in f.outliers else '']
                    for k, ((n, a, b), p, e) in enumerate(zip(pairs, f.predicted, f.residuals))]
            rows += [[], [tr('наклон'), f.slope], [tr('свободный член'), f.intercept], ['n', f.n], ['r', f.r],
                     ['R²', f.r2], ['Q²(LOO)', '' if f.q2 is None else f.q2], ['RMSE', f.rmse]]
            tables['fit'] = ([tr('Структура'), x, y, tr('y по прямой'), tr('остаток'), ''], rows)
        try:
            written = field_tables.write_tables(self.queue.folder, 'descriptors', tables)
        except OSError as exc:
            self.owner.error(exc)
            return []
        if hasattr(self.owner, 'notify'):
            self.owner.notify(tr('Таблицы — в папке «Анализ» очереди.'), 10000)
        return written

    def save_picture(self, path=None):
        if path is None:
            from modules.spectrum.wavefunction import field_tables

            start = str(field_tables.analysis_folder(self.queue.folder) / 'descriptors_fit.png')
            from azimuth import picture_export

            path = picture_export.ask(self, start)
            if not path:
                return None
        from azimuth import picture_export

        picture_export.save(self.plot, path, 'Azimuth · descriptors')  # PNG or SVG, white (0.249.2)
        return Path(path)
