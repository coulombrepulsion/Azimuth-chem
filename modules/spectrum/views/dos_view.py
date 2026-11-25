"""The tab «Плотность состояний» of Spectrum: DOS, PDOS of fragments, OPDOS (modules/spectrum/analysis/dos.py).

§1 PURPOSE
    For a complex: which orbitals are of the metal (its d), which of the ligands, where the HOMO–LUMO gap is; the
    OPDOS of two fragments — bonding (above zero) or antibonding (below).
§2 ALGORITHM
    The orbitals of the result are read once when the tab is first shown (load(source)); the fragments are the
    elements (the heaviest first) or the atoms chosen in Compass and the rest; the curves are redrawn on every change of
    the width, the shape, the spin or the pair of the OPDOS.
§4 SPECIFICATION
    DosPanel(): set_source(loader, chosen=None) — loader() -> (OrbitalSet, name) | None, chosen() -> set of atoms;
    load() -> bool; clear(); refresh(); plot (DosPlot: data dict of dos.curves, names); export(path).
§7 TESTS tests/test_gui.py::test_density_of_states_tab.
"""

from pathlib import Path

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from azimuth.i18n import tr
from azimuth.ui import card
from modules.spectrum.analysis import dos

COLOURS = ('#e0a040', '#3fb68b', '#d0607a', '#9a7ad8', '#4fb0d0', '#c8b040', '#8a9aa8', '#e07848')


class DosPlot(QWidget):
    LEFT, RIGHT, TOP, BOTTOM = 56, 20, 26, 40

    def __init__(self):
        super().__init__()
        self.data = None
        self.setMinimumHeight(260)

    def set_data(self, data):
        self.data = data
        self.update()

    def point(self, e, value, lo, hi, low, top):
        w = max(1, self.width() - self.LEFT - self.RIGHT)
        h = max(1, self.height() - self.TOP - self.BOTTOM)
        return QPointF(self.LEFT + (e - lo) / (hi - lo) * w, self.TOP + h - (value - low) / (top - low) * h)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), self.palette().base())
        from azimuth.ui import frame_plot  # the border of the plot (light theme)

        frame_plot(p, self)
        text = self.palette().text().color()
        p.setPen(text)
        d = self.data
        if not d:
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, tr('Нет орбиталей результата'))
            return
        x = d['x']
        lo, hi = float(x[0]), float(x[-1])
        top = max(1e-9, float(d['total'].max()) * 1.08)
        low = 0.0
        if d.get('opdos') is not None:
            low = min(0.0, float(d['opdos'].min()) * 1.15)
            top = max(top, float(d['opdos'].max()) * 1.15)
        # the share of an element
        # (Mulliken) can be below zero in an empty orbital — the scale takes it in, the zero line is drawn
        for _, y in d['parts']:
            low = min(low, float(y.min()) * 1.15)
        p.drawText(6, 16, tr('Плотность состояний, 1/эВ'))
        p.drawText(self.LEFT, self.height() - 10, f'{lo:.1f}')
        p.drawText(self.width() - self.RIGHT - 34, self.height() - 10, f'{hi:.1f}')
        p.drawText(self.width() // 2 - 30, self.height() - 10, tr('E, эВ'))
        p.setPen(QPen(self.palette().mid().color(), 1))
        base = self.height() - self.BOTTOM
        p.drawLine(self.LEFT, self.TOP, self.LEFT, base)
        p.drawLine(self.LEFT, base, self.width() - self.RIGHT, base)
        if low < 0:
            p.drawLine(self.point(lo, 0, lo, hi, low, top), self.point(hi, 0, lo, hi, low, top))
        # the levels: short ticks under the axis — occupied in colour, empty grey
        for e, n in d['levels']:
            if lo <= e <= hi:
                p.setPen(QPen(QColor('#6ea2f0' if n > 1e-6 else '#8a94a3'), 1.4))
                xx = self.point(e, 0, lo, hi, low, top).x()
                p.drawLine(QPointF(xx, base + 3), QPointF(xx, base + 11))
        if d.get('homo') is not None and lo <= d['homo'] <= hi:  # the HOMO, dashed
            p.setPen(QPen(QColor('#8a94a3'), 1, Qt.PenStyle.DashLine))
            xx = self.point(d['homo'], 0, lo, hi, low, top).x()
            p.drawLine(QPointF(xx, self.TOP), QPointF(xx, base))
            p.drawText(QPointF(xx + 4, self.TOP + 12), tr('ВЗМО'))

        def curve(y, pen):
            path = QPainterPath()
            path.moveTo(self.point(x[0], y[0], lo, hi, low, top))
            for a, b in zip(x[1:], y[1:]):
                path.lineTo(self.point(a, b, lo, hi, low, top))
            p.setPen(pen)
            p.drawPath(path)

        curve(d['total'], QPen(QColor('#6ea2f0'), 2))
        legend = [(tr('всего'), '#6ea2f0')]
        for k, (name, y) in enumerate(d['parts']):
            colour = COLOURS[k % len(COLOURS)]
            curve(y, QPen(QColor(colour), 1.5))
            legend.append((name, colour))
        if d.get('opdos') is not None:
            curve(d['opdos'], QPen(QColor('#e0709a'), 1.6, Qt.PenStyle.DashLine))
            legend.append((tr('OPDOS ') + d.get('pair_name', ''), '#e0709a'))
        self.draw_legend(p, legend, d, lo, hi)

    def draw_legend(self, p, legend, d, lo, hi):
        """The names of the curves on a plate of the colour of the plot, in the upper corner where the
        curves are lower — the right one unless the left part of the plot is the emptier."""
        metrics = p.fontMetrics()
        lines = ['— ' + name[:28] for name, _ in legend]
        width = max(metrics.horizontalAdvance(t) for t in lines) + 16
        height = metrics.height() * len(lines) + 10
        x, total = d['x'], d['total']
        n = len(x)
        quarter = max(1, n // 4)
        left_high, right_high = float(total[:quarter].max()), float(total[-quarter:].max())
        right = right_high <= left_high
        box_x = (self.width() - self.RIGHT - width - 6) if right else (self.LEFT + 8)
        box = QRectF(box_x, self.TOP + 2, width, height)
        plate = QColor(self.palette().base().color())
        plate.setAlpha(232)
        edge = QColor(self.palette().mid().color())
        edge.setAlpha(120)
        p.setPen(QPen(edge, 1))
        p.setBrush(plate)
        p.drawRoundedRect(box, 6, 6)
        p.setBrush(Qt.BrushStyle.NoBrush)
        y = box.top() + 5 + metrics.ascent()
        for (name, colour), line in zip(legend, lines):
            p.setPen(QColor(colour))
            p.drawText(QPointF(box.left() + 8, y), line)
            y += metrics.height()
        self.legend_box = box
        return box


class DosPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.loader = self.chosen = None
        self.orbital_set = None
        self.source = ''
        self.data = None
        column = QVBoxLayout(self)
        box, layout = card(tr('Плотность состояний'))
        layout.setContentsMargins(14, 12, 14, 14)
        layout.setSpacing(10)
        column.addWidget(box, 1)
        self.plot = DosPlot()
        layout.addWidget(self.plot, 1)
        row = QHBoxLayout()
        row.setSpacing(8)
        self.fragments = QComboBox()
        self.fragments.addItem(tr('По элементам'), 'elements')
        self.fragments.addItem(tr('Выделенные в Компасе атомы и остальные'), 'chosen')
        self.fragments.setToolTip(tr('На что делить состояния: по элементам (металл, лиганды) или на атомы, выделенные '
                                     'в Компасе, и все остальные'))
        self.fwhm = QDoubleSpinBox()
        self.fwhm.setRange(0.05, 3.0)
        self.fwhm.setSingleStep(0.05)
        self.fwhm.setValue(0.3)
        self.fwhm.setSuffix(tr(' эВ'))
        self.fwhm.setToolTip(tr('Ширина линии на половине высоты (FWHM)'))
        self.fwhm.setMaximumWidth(116)
        self.shape = QComboBox()
        self.shape.addItem(tr('Гаусс'), 'gauss')
        self.shape.addItem(tr('Лоренц'), 'lorentz')
        self.spin = QComboBox()
        self.spin.addItem('α', 'alpha')
        self.spin.addItem('β', 'beta')
        self.spin.setToolTip(tr('Орбитали α или β (открытая оболочка)'))
        self.opdos = QCheckBox(tr('OPDOS'))
        self.opdos.setToolTip(tr('Заселённость перекрывания двух фрагментов по энергии: выше нуля — связывающие '
                                 'орбитали, ниже — разрыхляющие'))
        self.pair_a, self.pair_b = QComboBox(), QComboBox()
        self.export_button = QPushButton(tr('Экспорт…'))
        self.export_button.clicked.connect(self.choose_export)
        for w in (self.fragments, QLabel(tr('Ширина')), self.fwhm, self.shape, self.spin, self.opdos, self.pair_a,
                  QLabel('↔'), self.pair_b):
            row.addWidget(w)
        row.addStretch(1)
        row.addWidget(self.export_button)
        layout.addLayout(row)
        self.note = QLabel()
        self.note.setObjectName('subtitle')
        self.note.setWordWrap(True)
        layout.addWidget(self.note)
        for w in (self.fragments, self.shape, self.spin, self.pair_a, self.pair_b):
            w.currentIndexChanged.connect(lambda *_: self.refresh())
        self.fwhm.valueChanged.connect(lambda *_: self.refresh())
        self.opdos.toggled.connect(lambda *_: self.refresh())
        self.clear()

    def set_source(self, loader, chosen=None):
        """loader() -> (OrbitalSet, name) | None — the orbitals of the result; chosen() -> the atoms chosen in Compass."""
        self.loader, self.chosen = loader, chosen
        self.clear()

    def clear(self):
        self.orbital_set, self.data = None, None
        self.plot.set_data(None)
        self.note.setText(tr('Плотность состояний строится по орбиталям результата при открытии вкладки.'))
        self.spin.hide()

    def load(self):
        """The orbitals of the result, once; True when there are some."""
        if self.orbital_set is not None:
            return True
        if self.loader is None:
            return False
        loaded = self.loader()
        if not loaded:
            self.note.setText(tr('В результате нет орбиталей — нужен файл орбиталей (Molden, fchk, .gbw ORCA).'))
            return False
        self.orbital_set, self.source = loaded
        self.spin.setVisible(self.orbital_set.unrestricted)
        self.refresh()
        return True

    def fragment_list(self):
        mol = self.orbital_set.molecule
        if self.fragments.currentData() == 'chosen' and self.chosen is not None:
            picked = sorted(a for a in self.chosen() if 0 <= a < len(mol.atoms))
            if picked and len(picked) < len(mol.atoms):
                rest = tuple(k for k in range(len(mol.atoms)) if k not in picked)
                names = '–'.join(f'{mol.atoms[k].symbol}{k + 1}' for k in picked[:4]) + ('…' if len(picked) > 4 else '')
                return [(names, tuple(picked)), (tr('остальные'), rest)]
        return dos.by_element(mol)

    def refresh(self):
        if self.orbital_set is None:
            return None
        fragments = self.fragment_list()
        for combo, default in ((self.pair_a, 0), (self.pair_b, 1)):
            names = [name for name, _ in fragments]
            if [combo.itemText(k) for k in range(combo.count())] != names:
                combo.blockSignals(True)
                combo.clear()
                combo.addItems(names)
                combo.setCurrentIndex(min(default, len(names) - 1))
                combo.blockSignals(False)
        pairing = self.opdos.isChecked() and len(fragments) > 1 and self.pair_a.currentIndex() != self.pair_b.currentIndex()
        for w in (self.pair_a, self.pair_b):
            w.setEnabled(self.opdos.isChecked())
        pair = (self.pair_a.currentIndex(), self.pair_b.currentIndex()) if pairing else None
        try:
            data = dos.curves(self.orbital_set, fragments, self.fwhm.value(), self.shape.currentData(),
                              spin=self.spin.currentData() if self.orbital_set.unrestricted else 'alpha', pair=pair)
        except ValueError as exc:
            self.note.setText(str(exc))
            return None
        if pair is not None:
            data['pair_name'] = f'{fragments[pair[0]][0]} ↔ {fragments[pair[1]][0]}'
        self.data = data
        self.plot.set_data(data)
        gap = (data['lumo'] - data['homo']) if data['homo'] is not None and data['lumo'] is not None else None
        self.note.setText(
            tr(f'Орбиталей: {len(data["levels"])}') + (tr(f' · ВЗМО {data["homo"]:.2f} эВ') if data['homo'] is not None else '')
            + (tr(f' · щель ВЗМО–НСМО {gap:.2f} эВ') if gap is not None else '')
            + ' · ' + tr('доли фрагментов — по Малликену; энергии орбиталей — из файла орбиталей'))
        return data

    def choose_export(self):
        path, _ = QFileDialog.getSaveFileName(self, tr('Экспорт плотности состояний'), str(Path.home() / 'dos.png'),
                                              tr('PNG (*.png);;SVG (*.svg);;CSV (*.csv)'))
        if path:
            self.export(Path(path))
        return path

    def export(self, path):
        from modules.spectrum.views.spectrum_common import _export_widget

        d = self.data
        if d is None:
            raise ValueError(tr('Плотность состояний ещё не построена.'))
        header = ['energy_eV', 'total'] + [name for name, _ in d['parts']] + (['opdos'] if d.get('opdos') is not None else [])
        columns = [d['x'], d['total']] + [y for _, y in d['parts']] + ([d['opdos']] if d.get('opdos') is not None else [])
        rows = np.column_stack(columns).tolist()
        _export_widget(self.plot, Path(path), 'Azimuth · DOS', rows, header)
        return path
