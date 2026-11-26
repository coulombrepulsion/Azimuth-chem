"""«Сравнить с экспериментом…» of the NMR tab: the computed shifts of one nucleus beside the measured ones.

§1 PURPOSE
    The window over modules/spectrum/analysis/nmr_compare.py: the measured shifts are typed in (one signal a line,
    with the numbers of its atoms or without), the table puts them beside the computed ones, the note gives the mean
    absolute error, the largest deviation, the straight line σ = a + b·δ_exp and the errors after its correction, and
    names the signals too close to be told apart; the plot — δ computed against δ measured with the line y = x.
§4 SPECIFICATION
    NMRCompareDialog(owner, rows, element, text='') — rows of orca_spectra.shifts for the element; .text
    (QPlainTextEdit), .table, .note, .plot (ShiftPlot: points [(exp, calc)], corrected [(exp, δ)]); compute() ->
    (pairs, stats | None, fit | None) or None with the reason in the note; copy(); save_csv(path=None) -> path.
    TOLERANCE {element: ppm} — computed signals nearer than this are called doubtful (H 0.1, C 2, others 5).
§7 TESTS
    tests/gui/test_gui_spectrum.py::test_nmr_compare_dialog.
"""

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QApplication, QDialog, QHBoxLayout, QPlainTextEdit, QVBoxLayout, QWidget

from azimuth.i18n import tr
from azimuth.ui import button, label
from modules.spectrum.analysis import nmr_compare
from modules.spectrum.views.tools_view import _fill, _save, _table

TOLERANCE = {'H': 0.1, 'C': 2.0}
OTHER_TOLERANCE = 5.0
HEADERS = ('Атомы', 'σ, м.д.', 'δ расчёт', 'δ эксперимент', 'Δ', 'δ с поправкой', 'Δ с поправкой')


class ShiftPlot(QWidget):
    """δ computed against δ measured: the points by the reference (filled) and after the linear correction (rings),
    the line y = x."""

    def __init__(self):
        super().__init__()
        self.points, self.corrected = [], []
        self.setMinimumHeight(220)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        every = [v for pair in self.points + self.corrected for v in pair]
        if not every:
            p.end()
            return
        lo, hi = min(every), max(every)
        pad = 0.08 * (hi - lo or 1.0)
        lo, hi = lo - pad, hi + pad
        side = max(60.0, min(self.width() - 80.0, self.height() - 60.0))
        left, top = 60.0, 12.0
        right, bottom = left + side, top + side

        def X(v):  # the shifts grow to the left, as in a spectrum
            return right - side * (v - lo) / (hi - lo)

        def Y(v):
            return bottom - side * (v - lo) / (hi - lo)

        font = QFont(self.font())
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(QPen(ink, 1))
        p.drawRect(QRectF(left, top, side, side))
        from math import floor, log10

        raw = (hi - lo) / 5
        power = 10 ** floor(log10(raw))
        step = next(m * power for m in (1, 2, 5, 10) if m * power >= raw)
        v = int(lo // step + 1) * step
        while v < hi:
            p.drawLine(QPointF(left - 4, Y(v)), QPointF(left, Y(v)))
            p.drawText(QRectF(0, Y(v) - 7, left - 6, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, f'{v:g}')
            p.drawLine(QPointF(X(v), bottom), QPointF(X(v), bottom + 4))
            p.drawText(QRectF(X(v) - 30, bottom + 6, 60, 14), Qt.AlignmentFlag.AlignCenter, f'{v:g}')
            v += step
        p.drawText(QRectF(left, bottom + 22, side, 14), Qt.AlignmentFlag.AlignCenter, tr('δ эксперимент, м.д.'))
        p.save()
        p.translate(12, (top + bottom) / 2)
        p.rotate(-90)
        p.drawText(QRectF(-110, -10, 220, 14), Qt.AlignmentFlag.AlignCenter, tr('δ расчёт, м.д.'))
        p.restore()
        p.setClipRect(QRectF(left, top, side, side))
        p.setPen(QPen(QColor('#888888'), 1, Qt.PenStyle.DashLine))
        p.drawLine(QPointF(X(lo), Y(lo)), QPointF(X(hi), Y(hi)))
        blue, green = QColor('#1f77b4'), QColor('#2e8b57')
        p.setPen(QPen(green, 1.6))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for x, y in self.corrected:
            p.drawEllipse(QPointF(X(x), Y(y)), 5.0, 5.0)
        p.setPen(QPen(blue, 1))
        p.setBrush(blue)
        for x, y in self.points:
            p.drawEllipse(QPointF(X(x), Y(y)), 3.2, 3.2)
        p.setClipping(False)
        p.setBrush(Qt.BrushStyle.NoBrush)
        x0 = right + 14
        if x0 + 150 < self.width():
            for k, (color, text, ring) in enumerate(((blue, tr('по опоре (TMS)'), False), (green, tr('с линейной поправкой'), True))):
                y = top + 10 + 18 * k
                p.setPen(QPen(color, 1.6))
                p.setBrush(Qt.BrushStyle.NoBrush if ring else color)
                p.drawEllipse(QPointF(x0, y), 4.0, 4.0)
                p.setPen(QPen(ink, 1))
                p.drawText(QRectF(x0 + 10, y - 7, 170, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, text)
        p.end()


class NMRCompareDialog(QDialog):
    def __init__(self, owner, rows, element, text=''):
        super().__init__(owner)
        self.setWindowTitle(tr('Сравнение с экспериментом') + f' · {element}')
        self.rows, self.element = list(rows), element
        self.found = None
        lay = QVBoxLayout(self)
        hint = label(tr('Экспериментальные сдвиги, м.д.: по одному сигналу в строке. Без номеров атомов сигналы '
                        'сопоставляются по порядку — так отнесение предлагает сам расчёт. С номерами («C1 77.2», '
                        '«H3 H4 H5 2.15») — по вашему отнесению; тогда можно ввести и часть спектра.'), 'subtitle')
        hint.setWordWrap(True)
        lay.addWidget(hint)
        top = QHBoxLayout()
        self.text = QPlainTextEdit()
        self.text.setPlaceholderText('171.2\n128.9\n61.5\n21.0')
        self.text.setPlainText(text)
        self.text.setMaximumWidth(260)
        self.text.textChanged.connect(lambda: self.compute())
        top.addWidget(self.text)
        self.plot = ShiftPlot()
        top.addWidget(self.plot, 1)
        lay.addLayout(top, 2)
        self.table = _table(HEADERS)
        lay.addWidget(self.table, 3)
        self.note = label('', 'subtitle')
        self.note.setWordWrap(True)
        self.note.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self.note)
        bottom = QHBoxLayout()
        bottom.addWidget(button(tr('Копировать таблицу'), lambda: self.copy()))
        bottom.addWidget(button(tr('Сохранить CSV…'), lambda: self.save_csv()))
        bottom.addStretch(1)
        bottom.addWidget(button(tr('Закрыть'), self.accept))
        lay.addLayout(bottom)
        self.resize(820, 700)
        self.compute()

    def names(self, atoms):
        return ', '.join(f'{self.element}{a + 1}' for a in atoms)

    def compute(self):
        self.found = None
        self.plot.points, self.plot.corrected = [], []
        try:
            measured = nmr_compare.parse(self.text.toPlainText())
            if not measured:
                _fill(self.table, [])
                self.note.setText(tr('Сигналов в расчёте: {}.').format(len(self.rows)))
                self.plot.update()
                return None
            pairs = nmr_compare.pairs(self.rows, measured)
        except ValueError as exc:
            _fill(self.table, [])
            self.note.setText(str(exc))
            self.plot.update()
            return None
        stats = nmr_compare.stats(pairs)
        try:
            fit = nmr_compare.linear(pairs)
        except ValueError:
            fit = None
        rows = []
        for k, pair in enumerate(pairs):
            scaled = fit.shifts[k] if fit else None
            rows.append((self.names(pair.atoms), f'{pair.sigma:.3f}', '—' if pair.calc is None else f'{pair.calc:.2f}',
                         f'{pair.exp:.2f}', '—' if pair.calc is None else f'{pair.calc - pair.exp:+.2f}',
                         '—' if scaled is None else f'{scaled:.2f}', '—' if scaled is None else f'{scaled - pair.exp:+.2f}'))
        _fill(self.table, rows)
        lines = []
        if stats is None:
            lines.append(tr('Нет опоры (TMS) для этого ядра: сдвиги по опоре не посчитаны, сравнение — только с '
                            'линейной поправкой.'))
        else:
            lines.append(tr('По опоре: MAE {} м.д., среднеквадратичная {} м.д., наибольшее отклонение {} м.д. ({}).').format(
                f'{stats.mae:.2f}', f'{stats.rmse:.2f}', f'{stats.largest:+.2f}', self.names(pairs[stats.largest_at].atoms)))
            self.plot.points = [(p.exp, p.calc) for p in pairs]
        if fit is None:
            lines.append(tr('Для линейной поправки нужны хотя бы три разных сигнала.'))
        else:
            lines.append(tr('Прямая σ = a + b·δэксп: a = {}, b = {}, r² = {}. После поправки δ = (σ − a)/b: MAE {} м.д., '
                            'наибольшее отклонение {} м.д. ({}).').format(
                f'{fit.a:.2f}', f'{fit.b:.4f}', f'{fit.r2:.4f}', f'{fit.stats.mae:.2f}', f'{fit.stats.largest:+.2f}',
                self.names(pairs[fit.stats.largest_at].atoms)))
            lines.append(tr('Прямая проведена по тем же сигналам, по которым считается ошибка: при малом числе сигналов '
                            'ошибка после поправки занижена.'))
            self.plot.corrected = [(p.exp, d) for p, d in zip(pairs, fit.shifts)]
        tolerance = TOLERANCE.get(self.element, OTHER_TOLERANCE)
        close = nmr_compare.doubtful(pairs, tolerance)
        if close:
            lines.append(tr('Расчётные сигналы ближе {} м.д. друг к другу — их отнесение по расчёту ненадёжно: {}.').format(
                f'{tolerance:g}', '; '.join(f'{self.names(pairs[i].atoms)} / {self.names(pairs[j].atoms)}' for i, j in close)))
        self.note.setText('\n'.join(lines))
        self.plot.update()
        self.found = (pairs, stats, fit)
        return self.found

    def copy(self):
        header = [self.table.horizontalHeaderItem(c).text() for c in range(self.table.columnCount())]
        rows = [[self.table.item(r, c).text() for c in range(self.table.columnCount())] for r in range(self.table.rowCount())]
        text = '\n'.join('\t'.join(row) for row in [header] + rows) + '\n' + self.note.text()
        QApplication.clipboard().setText(text)
        return text

    def save_csv(self, path=None):
        return _save(self, self.table, path, f'nmr_{self.element}_experiment.csv')
