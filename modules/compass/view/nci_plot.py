"""The plot RDG (or IRI) — sign(λ₂)ρ of an NCI analysis from Multiwfn.

§1 PURPOSE
    The two-dimensional picture of the NCI paper (Johnson et al. 2010): every grid point is a dot (sign(λ₂)ρ, s).
    Where s falls to zero at small density there is an interaction: spikes at sign(λ₂)ρ ≈ −0.02 … −0.04 a.u. are
    hydrogen bonds, near 0 — van der Waals contacts, at positive values — steric repulsion. The dots have the colours
    of the surface on the model (compass/surfaces.nci_colors); the dashed line is the level of that surface.
§2 ALGORITHM
    multiwfn.scatter chooses the points in the window multiwfn.PLOT_WINDOWS (at most 60 000); QPainter draws them in
    a few colour bands (drawPoints per band), the axes, the ticks and the level line. «Сохранить PNG…» grabs the plot.
    The domains of the surface (modules/spectrum/analysis/nci_domains.py) — every spike numbered and named on
    the plot (a mark at (spike, lowest RDG of the domain) and its number), the table of the domains under it (the
    criteria in the tooltip of a row); a row chosen marks its spike and, through choose(index), its domain on the model.
§4 SPECIFICATION NciPanel(parent): set_result(sign_cube, field_cube, kind ('nci' | 'iri' | 'igmh'), title, level=None,
    domains=(), symbols=(), choose=None, pairs=(), atoms=None) -> NciPlot (points (xs, ys), window, top, level, marks
    [(x, y, number, colour)], chosen); save_png(path=None); .table (QTableWidget, a row per domain); choose_row(row).
    Fragments=(), kind 'igmh' — the plot δg_inter — sign(λ₂)ρ (the peaks up, the axis to the highest peak: nice_top),
    .pairs_table (the IGMH atom pairs [(i, j, δG, …)], at most PAIRS) and .atoms_note (the atoms {atom: δG} with the
    largest share). The tab «NCI» of Spectrum instead of the window NciPlotDialog.
§7 TESTS
    tests/test_gui.py::test_multiwfn_nci_on_the_model.
"""

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QAbstractItemView, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QPushButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from modules.compass.view import surfaces
from modules.spectrum.wavefunction import multiwfn
from azimuth.i18n import tr

BANDS = 24


def nice_top(value):
    """The round number (1, 2, 2.5, 5 × 10ⁿ) at or above value: the top of the axis of δg_inter."""
    import math

    power = 10 ** math.floor(math.log10(value))
    for m in (1, 2, 2.5, 5, 10):
        if m * power >= value - 1e-15:
            return m * power
    return 10 * power


class NciPlot(QWidget):
    LEFT, RIGHT, TOP, BOTTOM = 58, 16, 14, 42

    def __init__(self, sign, field, kind, level, parent=None, domains=()):
        super().__init__(parent)
        self.kind = kind
        self.window, self.top = multiwfn.PLOT_WINDOWS[kind]
        rdg = np.asarray(field.values)[..., 0].reshape(-1)
        low, high = self.window
        floor = 0.0
        if kind == 'igmh':  # δg_inter — the peaks go up; the axis up to the highest one in the window
            signs = np.asarray(sign.values)[..., 0].reshape(-1)
            inside = rdg[(signs >= low) & (signs <= high)]
            peak = float(inside.max()) if inside.size else 0.0
            self.top = nice_top(peak * 1.1) if peak > 0 else self.top
            floor = self.top * 0.002
        self.points = multiwfn.scatter(sign, field, self.window, self.top, floor=floor)
        self.level = level
        self.marks = []  # (spike, lowest RDG of the domain, number, colour) of every domain in the window
        colours = surfaces.nci_colors([d.peak for d in domains]) if domains else []
        for k, (d, rgb) in enumerate(zip(domains, colours)):
            if low <= d.peak <= high and len(d.nodes):
                y = float(rdg[d.nodes].max() if kind == 'igmh' else rdg[d.nodes].min())
                self.marks.append((d.peak, y, k + 1, QColor.fromRgbF(*rgb)))
        self.chosen = None
        self.setMinimumSize(520, 300)

    def map(self, x, y):
        w = self.width() - self.LEFT - self.RIGHT
        h = self.height() - self.TOP - self.BOTTOM
        low, high = self.window
        return self.LEFT + (x - low) / (high - low) * w, self.TOP + (1 - y / self.top) * h

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self.palette().window().color().lightness() < 128
        ink = QColor('#c9d1dc' if dark else '#3b4657')
        grid = QColor('#2a3442' if dark else '#e3e7ee')
        p.fillRect(self.rect(), QColor('#11151c' if dark else '#ffffff'))
        low, high = self.window
        font = QFont(self.font())
        font.setPixelSize(11)
        p.setFont(font)
        # the grid and the ticks
        step_x = 0.1 if self.kind == 'iri' else 0.01
        ticks_x = np.arange(np.ceil(low / step_x) * step_x, high + 1e-12, step_x)
        ticks_y = np.arange(0, self.top + 1e-12, 0.5 if self.kind != 'igmh' else self.top / 5)
        for t in ticks_x:
            x0, y0 = self.map(t, 0)
            _, y1 = self.map(t, self.top)
            p.setPen(QPen(grid, 1))
            p.drawLine(QPointF(x0, y0), QPointF(x0, y1))
            p.setPen(ink)
            p.drawText(QRectF(x0 - 30, y0 + 4, 60, 14), Qt.AlignmentFlag.AlignHCenter, ('0' if abs(t) < 1e-9 else f'{t:+.2f}'.replace('-', '−')))
        for t in ticks_y:
            x0, y0 = self.map(low, t)
            x1, _ = self.map(high, t)
            p.setPen(QPen(grid, 1))
            p.drawLine(QPointF(x0, y0), QPointF(x1, y0))
            p.setPen(ink)
            p.drawText(QRectF(0, y0 - 7, self.LEFT - 6, 14), Qt.AlignmentFlag.AlignRight, f'{t:.4g}')
        # the points, in colour bands
        xs, ys = self.points
        if len(xs):
            bands = np.minimum((np.clip((xs - surfaces.NCI_LOW) / (surfaces.NCI_HIGH - surfaces.NCI_LOW), 0, 1) * BANDS).astype(int), BANDS - 1)
            colors = surfaces.nci_colors(surfaces.NCI_LOW + (np.arange(BANDS) + 0.5) / BANDS * (surfaces.NCI_HIGH - surfaces.NCI_LOW))
            p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
            for band in range(BANDS):
                chosen = bands == band
                if not chosen.any():
                    continue
                p.setPen(QPen(QColor.fromRgbF(*colors[band]), 2))
                p.drawPoints([QPointF(*self.map(x, y)) for x, y in zip(xs[chosen], ys[chosen])])
            p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # the spikes of the domains — a mark under the dip and its number; the chosen one larger
        rows = []
        for x, y, number, colour in sorted(self.marks, key=lambda m: m[0]):
            px, py = self.map(x, min(y, self.top))
            lift = 0
            for qx, qlift in rows:  # numbers close along x stacked upwards
                if abs(qx - px) < 22:
                    lift = max(lift, qlift + 16)
            rows.append((px, lift))
            chosen = number - 1 == self.chosen
            r = 5.5 if chosen else 4.0
            p.setPen(QPen(ink, 1.4 if chosen else 1.0))
            p.setBrush(colour)
            p.drawEllipse(QPointF(px, py), r, r)
            p.setBrush(Qt.BrushStyle.NoBrush)
            bold = QFont(font)
            bold.setBold(chosen)
            p.setFont(bold)
            text_y = max(py - 22 - lift, self.TOP)  # a peak at the top of the axis: the number stays inside
            p.drawText(QRectF(px - 20, text_y, 40, 14), Qt.AlignmentFlag.AlignHCenter, str(number))
            p.setFont(font)
        # the level of the surface on the model
        if self.level is not None and 0 < self.level < self.top:
            x0, y0 = self.map(low, self.level)
            x1, _ = self.map(high, self.level)
            p.setPen(QPen(ink, 1, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(x0, y0), QPointF(x1, y0))
        # the axes
        p.setPen(QPen(ink, 1))
        x0, y0 = self.map(low, 0)
        x1, y1 = self.map(high, self.top)
        p.drawRect(QRectF(x0, y1, x1 - x0, y0 - y1))
        p.drawText(QRectF(self.LEFT, self.height() - 20, self.width() - self.LEFT - self.RIGHT, 16),
                   Qt.AlignmentFlag.AlignHCenter, tr('sign(λ₂)ρ, а. е.'))
        p.save()
        p.translate(14, self.TOP + (self.height() - self.TOP - self.BOTTOM) / 2)
        p.rotate(-90)
        p.drawText(QRectF(-80, -8, 160, 16), Qt.AlignmentFlag.AlignHCenter,
                   'IRI' if self.kind == 'iri' else tr('δg_inter, а. е.') if self.kind == 'igmh' else tr('RDG, s'))
        p.restore()
        p.end()


HINTS = {
    'igmh': 'Пики δg_inter — взаимодействия между молекулами: слева (синее) — водородные связи, у нуля (зелёное) — '
            'ван-дер-ваальсовы, справа (красное) — отталкивание. Пунктир — уровень поверхности на модели. Номера пиков — '
            'строки таблицы и метки на модели; ниже — вклад пар атомов (индексы δG IGMH).',
    'nci': 'Провалы RDG к нулю — взаимодействия: слева (синее) — водородные связи, у нуля (зелёное) — ван-дер-ваальсовы, '
           'справа (красное) — отталкивание. Пунктир — уровень поверхности на модели. Номера провалов — строки таблицы '
           'и метки на модели.',
    'iri': 'Провалы IRI — связи (далеко слева) и слабые взаимодействия (у нуля). Пунктир — уровень поверхности на модели.',
}


class NciPanel(QWidget):
    """The tab «NCI» of Spectrum — the plot of the last NCI or IRI analysis put on the Compass model; empty
    until there is one."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot = None
        self.result = None
        layout = QVBoxLayout(self)
        self.title = QLabel(tr('Посчитайте NCI или IRI в Компасе: «Поверхность на модели → Слабые взаимодействия».'))
        self.title.setObjectName('subtitle')
        self.title.setWordWrap(True)
        layout.addWidget(self.title)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        layout.addWidget(self.hint)
        self.host = QVBoxLayout()
        # until NCI or IRI is computed — Quill with the flag at the middle of a bond (docs/art/QUAIL_ART_DIALOGS.md)
        from azimuth import quill

        self.empty_note = quill.EmptyNote('', 'no-points')
        self.host.addWidget(self.empty_note, 1, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(self.host, 3)
        # the domains — a row per weak interaction
        self.domains = ()
        self.choose = None
        self.table = QTableWidget(0, 0)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.table.verticalHeader().setVisible(True)
        self.table.itemSelectionChanged.connect(self._selected)
        self.table.hide()
        layout.addWidget(self.table, 2)
        # IGMH — the atoms and the atom pairs that make the interactions
        self.atoms_note = QLabel()
        self.atoms_note.setWordWrap(True)
        self.atoms_note.hide()
        layout.addWidget(self.atoms_note)
        self.pairs_table = QTableWidget(0, 0)
        self.pairs_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.pairs_table.hide()
        layout.addWidget(self.pairs_table, 2)
        row = QHBoxLayout()
        row.addStretch(1)
        self.save_button = QPushButton(tr('Сохранить PNG…'))
        self.save_button.clicked.connect(self.save_png)
        self.save_button.setEnabled(False)
        row.addWidget(self.save_button)
        layout.addLayout(row)

    def set_result(self, sign, field, kind, title, level=None, domains=(), symbols=(), choose=None, pairs=(), atoms=None,
                   fragments=()):
        if self.plot is not None:
            self.host.removeWidget(self.plot)
            self.plot.deleteLater()
        self.plot = NciPlot(sign, field, kind, level, domains=domains)
        self.fill_table(domains, symbols)
        self.fill_pairs(pairs, atoms or {}, symbols, fragments)
        self.choose = choose
        self.empty_note.hide()
        self.host.addWidget(self.plot, 1)
        self.result = (kind, title)
        self.title.setText(title)
        self.hint.setText(tr(HINTS[kind]))
        self.save_button.setEnabled(True)
        return self.plot

    def fill_table(self, domains, symbols):
        from modules.spectrum.analysis import nci_domains

        self.domains = tuple(domains)
        self.table.blockSignals(True)
        self.table.clearSelection()
        if not self.domains:
            self.table.setRowCount(0)
            self.table.hide()
            self.table.blockSignals(False)
            return
        header, rows = nci_domains.table(self.domains, list(symbols))
        self.table.setColumnCount(len(header))
        self.table.setHorizontalHeaderLabels(header)
        self.table.setRowCount(len(rows))
        for r, (d, row) in enumerate(zip(self.domains, rows)):
            tip = nci_domains.detail(d, list(symbols))
            for c, text in enumerate(row):
                item = QTableWidgetItem(text)
                item.setToolTip(tip)
                if c in (2, 4, 5, 6, 7, 8, 10):  # the numbers
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(r, c, item)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.show()
        self.table.blockSignals(False)

    PAIRS = 20

    def fill_pairs(self, pairs, atoms, symbols, fragments=()):
        """The atom pairs of IGMH with the largest δG (at most PAIRS) and their share of all pairs; above, the
        atoms with the largest share of each molecule (fragment), as Multiwfn counts them."""
        def name(k):
            return f'{symbols[k]}{k + 1}' if 0 <= k < len(symbols) else str(k + 1)

        self.pairs = tuple(pairs)
        if not self.pairs:
            self.pairs_table.setRowCount(0)
            self.pairs_table.hide()
            self.atoms_note.hide()
            return
        total = sum(p[2] for p in self.pairs) or 1.0
        groups = [list(f) for f in fragments] or [sorted(atoms)]
        parts = []
        for n, members in enumerate(groups):
            mine = {k: atoms[k] for k in members if atoms.get(k)}
            whole = sum(mine.values())
            if whole <= 0:
                continue
            best = sorted(mine.items(), key=lambda a: -a[1])[:3]
            parts.append(tr(f'молекула {n + 1}: ') + ', '.join(f'{name(k)} {100 * v / whole:.0f} %' for k, v in best))
        self.atoms_note.setText(tr('Атомы с наибольшим вкладом (IGMH) — ') + '; '.join(parts))
        self.atoms_note.setVisible(bool(parts))
        header = [tr('Пара атомов'), tr('δG пары, а. е.'), tr('Доля, %')]
        rows = self.pairs[:self.PAIRS]
        self.pairs_table.setColumnCount(len(header))
        self.pairs_table.setHorizontalHeaderLabels(header)
        self.pairs_table.setRowCount(len(rows))
        for r, (i, j, value, *_) in enumerate(rows):
            for c, text in enumerate((f'{name(i)}···{name(j)}', f'{value:.4f}', f'{100 * value / total:.1f}')):
                item = QTableWidgetItem(text)
                if c:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.pairs_table.setItem(r, c, item)
        self.pairs_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.pairs_table.show()

    def _selected(self):
        rows = self.table.selectionModel().selectedRows() if self.table.selectionModel() else []
        self.choose_row(rows[0].row() if rows else None)

    def choose_row(self, row):
        """The domain of a row (or None) marked on the plot and, through choose, on the model."""
        if self.plot is not None:
            self.plot.chosen = row
            self.plot.update()
        if self.choose is not None:
            self.choose(row)
        return row

    def save_png(self, path=None):
        if self.plot is None:
            return None
        if not path:
            path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить PNG…'), 'nci.png', tr('PNG (*.png)'))
        if path:
            self.plot.grab().save(str(path), 'PNG')
        return path or None
