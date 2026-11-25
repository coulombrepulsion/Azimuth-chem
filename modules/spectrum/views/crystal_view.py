"""Spectrum of a project of a crystal: the results of its calculations.

§1 PURPOSE
    Spectrum for a crystal: the plots of the optimization, the bands and the density of states, the charges and the
    bonds of the runs of the project of the crystal shown (crystal_results).
§2 LAYOUT
    As the page of a molecule: one frame, the tabs on its top edge; at its foot the name of the project, the
    line of the run (its energy, steps, the cell computed and, for a supercell, the cell of the file it gives) and the
    list of the runs (the newest chosen). The tabs of the run: «Энергия и шаги» — the card of the steps (the table) and
    the card of the plots: ΔE per atom against the last step (meV/atom) and the change of the cell from the start (Δa,
    Δb, Δc, ΔV in %); for an energy or no run, Quill with her hint in place of the plots;
    «Зоны» and «Плотность состояний» — the plots of the panel of Quantum ESPRESSO (qe_plots) when the run has them;
    «Заряды» and «Связи AIM» — the tables of Multiwfn of a CP2K run (kept beside it, or computed by their button).
    A tab with nothing for the run is hidden.
§4 SPECIFICATION
    CrystalResultsView(window): show_project(manifest, title) -> number of runs; choose(index); tabs, runs (combo),
    line, energy_plot, cell_plot, steps_table, bands_plot, dos_plot, charges_table, aim_table, the buttons.
§7 TESTS
    tests/gui/test_gui_files.py::test_the_spectrum_of_a_crystal.
"""

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (QComboBox, QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.actions.qe_plots import BandsPlot, DosPlot, _Plot

COLORS = ('#2a62b8', '#c0504d', '#3a9a5b', '#b8893f')
EV_MEV = 1000.0
HARTREE_EV = 27.211386245988


def _nice(lo, hi):
    import math

    span = hi - lo or abs(hi) or 1.0
    step = 10 ** math.floor(math.log10(span / 4))
    for k in (1, 2, 5, 10):
        if span / (step * k) <= 6:
            step *= k
            break
    ticks, v = [], math.floor(lo / step) * step
    while v <= hi + step * 0.01:
        if v >= lo - step * 0.01:
            ticks.append(round(v, 10))
        v += step
    return ticks or [lo, hi]


class StepPlot(_Plot):
    """Lines against the step: series [(label, values)], the label of the axis of values."""

    LEFT = 64

    def __init__(self, ylabel=''):
        super().__init__()
        self.setMinimumSize(360, 260)
        self.series, self.ylabel = [], ylabel

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        left, right, top, bottom = self.frame()
        values = [v for _, vs in self.series for v in vs if v is not None]
        font = QFont(self.font())
        font.setPixelSize(11)
        p.setFont(font)
        p.setPen(QPen(ink, 1))
        p.drawRect(QRectF(left, top, right - left, bottom - top))
        if not values:
            p.end()
            return
        n = max(len(vs) for _, vs in self.series)
        lo, hi = min(values), max(values)
        if hi - lo < 1e-12:
            lo, hi = lo - 1, hi + 1
        pad = (hi - lo) * 0.08
        lo, hi = lo - pad, hi + pad

        def X(k):
            return left + (right - left) * (k / (n - 1) if n > 1 else 0.5)

        def Y(v):
            return bottom - (bottom - top) * (v - lo) / (hi - lo)

        for v in _nice(lo, hi):
            if lo <= v <= hi:
                p.drawLine(QPointF(left - 4, Y(v)), QPointF(left, Y(v)))
                p.drawText(QRectF(0, Y(v) - 7, left - 6, 14), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
                           f'{v:g}'.replace('-', '−'))
        every = max(1, (n - 1) // 10 + 1)
        for k in range(0, n, every):
            p.drawLine(QPointF(X(k), bottom), QPointF(X(k), bottom + 4))
            p.drawText(QRectF(X(k) - 16, bottom + 6, 32, 14), Qt.AlignmentFlag.AlignCenter, str(k))
        p.drawText(QRectF(right - 120, bottom + 18, 120, 14), Qt.AlignmentFlag.AlignRight, tr('шаг'))
        p.save()
        p.translate(12, (top + bottom) / 2)
        p.rotate(-90)
        p.drawText(QRectF(-110, -10, 220, 14), Qt.AlignmentFlag.AlignCenter, self.ylabel)
        p.restore()
        if lo < 0 < hi:
            p.setPen(QPen(ink, 0.6, Qt.PenStyle.DashLine))
            p.drawLine(QPointF(left, Y(0)), QPointF(right, Y(0)))
        y = top + 6
        for k, (label, vs) in enumerate(self.series):
            color = QColor(COLORS[k % len(COLORS)])
            path, started = QPainterPath(), False
            for i, v in enumerate(vs):
                if v is None:
                    continue
                point = QPointF(X(i), Y(v))
                if started:
                    path.lineTo(point)
                else:
                    path.moveTo(point)
                started = True
            p.setPen(QPen(color, 1.8))
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawPath(path)
            p.setBrush(color)
            for i, v in enumerate(vs):
                if v is not None:
                    p.drawEllipse(QPointF(X(i), Y(v)), 2.6, 2.6)
            if len(self.series) > 1:
                p.drawLine(QPointF(right - 96, y + 6), QPointF(right - 80, y + 6))
                p.setPen(QPen(ink, 1))
                p.drawText(QRectF(right - 76, y, 72, 14), Qt.AlignmentFlag.AlignLeft, label)
                y += 15
        p.end()


def _table(heads):
    table = QTableWidget(0, len(heads))
    table.setHorizontalHeaderLabels(heads)
    table.verticalHeader().setVisible(False)
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)  # the columns share the width
    return table


def _fill(table, rows):
    table.setRowCount(len(rows))
    for r, row in enumerate(rows):
        for c, value in enumerate(row):
            text = str(value)
            if text[:1] == '-' and text[1:2].isdigit():
                text = '−' + text[1:]  # the sign of minus, as in the labels of Compass
            table.setItem(r, c, QTableWidgetItem(text))


class CrystalResultsView(QWidget):
    def __init__(self, window):
        super().__init__()
        self.window_, self.manifest, self.title, self.run_list, self.run = window, None, '', [], None
        # the page is built as that of a molecule
        # (modules/spectrum/workspace.py) — one frame, the tabs on its top edge, in the first tab two cards (the table
        # left, the plots or Quill with her hint right), the run and its line at the foot
        from azimuth import quill
        from azimuth.ui import card, label
        from modules.spectrum.results_page import ResultTabs

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.panel, layout = card('')
        heading = layout.itemAt(0).widget()
        layout.removeWidget(heading)
        heading.deleteLater()
        layout.setSpacing(10)
        layout.setContentsMargins(14, 12, 14, 12)
        outer.addWidget(self.panel, 1)
        self.tabs = ResultTabs()
        # the tabs lie on the panel of the group, 12 px in — past its rounded corner
        tabs_row = QHBoxLayout()
        tabs_row.setContentsMargins(12, 0, 2, 0)
        tabs_row.addWidget(self.tabs.header, 0, Qt.AlignmentFlag.AlignBottom)
        tabs_row.addStretch(1)
        layout.setSpacing(0)
        layout.addLayout(tabs_row)
        layout.addWidget(self.tabs.group(), 1)  # the list of the pages and the page, on one panel
        layout.addSpacing(10)
        foot = QHBoxLayout()  # the status at the foot, as «Завершение … · Последняя энергия» of a molecule
        foot.setSpacing(14)
        status = QVBoxLayout()
        status.setSpacing(0)
        self.heading = label('', 'subtitle')
        status.addWidget(self.heading)
        self.line = label('', 'subtitle')
        self.line.setWordWrap(True)
        self.line.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        status.addWidget(self.line)
        foot.addLayout(status, 1)
        self.runs_label = QLabel(tr('Расчёт'))
        foot.addWidget(self.runs_label)
        self.runs = QComboBox()
        self.runs.setMinimumWidth(320)
        self.runs.currentIndexChanged.connect(self.choose)
        foot.addWidget(self.runs)
        layout.addLayout(foot)

        # Quill with her magnifier and the hint, in the card of the plots in place of them (as in the card of the
        # frequencies of a molecule): no run yet, an energy (one step) or an output without steps
        self.empty = QWidget()
        column = QVBoxLayout(self.empty)
        column.addStretch(1)
        self.empty_quill = QLabel()
        self.empty_quill.setObjectName('emptyQuill')
        self.empty_quill.setProperty('quill', True)  # hides the scales of the hub, as on the page of a molecule
        picture = quill.pixmap('empty-result', 150)
        if not picture.isNull():
            self.empty_quill.setPixmap(picture)
        column.addWidget(self.empty_quill, 0, Qt.AlignmentFlag.AlignHCenter)
        self.empty_text = label(tr(self.EMPTY_TEXT), 'subtitle')
        self.empty_text.setWordWrap(True)
        self.empty_text.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.empty_text.setMaximumWidth(520)
        column.addWidget(self.empty_text, 0, Qt.AlignmentFlag.AlignHCenter)
        column.addStretch(1)

        page = QWidget()
        row = QHBoxLayout(page)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(12)
        card_steps, box = card(tr('Шаги · энергия и ячейка'))
        box.setContentsMargins(14, 12, 14, 14)
        self.steps_table = _table([tr('Шаг'), tr('E, Eh'), tr('ΔE, мэВ/атом'), 'a, Å', 'b, Å', 'c, Å', 'V, Å³'])
        box.addWidget(self.steps_table, 1)
        card_plots, box = card(tr('Оптимизация · по шагам'))
        box.setContentsMargins(14, 12, 14, 14)
        self.energy_plot = StepPlot(tr('E − E(конец), мэВ/атом'))
        self.cell_plot = StepPlot(tr('изменение от начала, %'))
        box.addWidget(self.energy_plot, 1)
        box.addWidget(self.cell_plot, 1)
        box.addWidget(self.empty, 1)
        row.addWidget(card_steps, 2)  # 2 : 3, as the energies
        row.addWidget(card_plots, 3)  # and the frequencies of a molecule (workspace.py)
        # the first tab is there for every run, as «Энергии и частоты» of a molecule — the steps of an optimization, or
        # the one row of an energy
        self.optimization_tab = self.tabs.addTab(page, tr('Энергия и шаги'))
        self.bands_plot, self.dos_plot = BandsPlot(), DosPlot()
        self.bands_tab = self.tabs.addTab(self.bands_plot, tr('Зоны'))
        # the DOS with its projections (crystal_pdos): by element or by s, p, d of each element
        page = QWidget()
        box = QVBoxLayout(page)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Проекции:')))
        self.projection = QComboBox()
        for key, name in (('elements', 'по элементам'), ('orbitals', 'по орбиталям s, p, d'), ('', 'только полная')):
            self.projection.addItem(tr(name), key)
        self.projection.currentIndexChanged.connect(lambda _: self.draw_dos())
        row.addWidget(self.projection)
        row.addStretch(1)
        box.addLayout(row)
        box.addWidget(self.dos_plot, 1)
        row = QHBoxLayout()
        self.dos_note = QLabel()
        self.dos_note.setWordWrap(True)
        row.addWidget(self.dos_note, 1)
        self.pdos_button = action_button(tr('Посчитать PDOS по волновой функции'), self.compute_pdos, 'pdos')
        row.addWidget(self.pdos_button)
        box.addLayout(row)
        self.dos_tab = self.tabs.addTab(page, tr('Плотность состояний'))
        self.pdos_found = None
        page = QWidget()
        box = QVBoxLayout(page)
        self.charges_table = _table([tr('Атом'), tr('Элемент'), tr('Хиршфельд'), 'CM5'])
        box.addWidget(self.charges_table, 1)
        row = QHBoxLayout()
        self.charges_note = QLabel()
        self.charges_note.setWordWrap(True)
        row.addWidget(self.charges_note, 1)
        self.charges_button = action_button(tr('Посчитать заряды в Multiwfn'), self.compute_charges, 'charges')
        row.addWidget(self.charges_button)
        box.addLayout(row)
        self.charges_tab = self.tabs.addTab(page, tr('Заряды'))
        page = QWidget()
        box = QVBoxLayout(page)
        self.aim_table = _table([tr('Связь'), tr('Длина, Å'), tr('Связей у атома'), 'ρ, a.u.', '∇²ρ, a.u.', 'H, a.u.',
                                 '|V|/G', tr('Тип взаимодействия')])
        box.addWidget(self.aim_table, 1)
        row = QHBoxLayout()
        self.aim_note = QLabel()
        self.aim_note.setWordWrap(True)
        row.addWidget(self.aim_note, 1)
        self.aim_button = action_button(tr('Посчитать связи по AIM в Multiwfn'), self.compute_aim, 'bond-orders')
        row.addWidget(self.aim_button)
        box.addLayout(row)
        self.aim_tab = self.tabs.addTab(page, tr('Связи AIM'))
        self.show_empty(True)

    # -- the project and its runs ---------------------------------------------------------------------------------------
    def show_project(self, manifest, title=''):
        from modules.compass.chemistry import crystal_results

        self.manifest, self.title = Path(manifest), title
        self.heading.setText(tr('{} — расчёты кристалла').format(title) if title else tr('Расчёты кристалла'))
        self.run_list = crystal_results.runs(manifest)
        self.runs.blockSignals(True)
        self.runs.clear()
        for run in self.run_list:
            when = run.time.replace('T', ' ')[:16]
            self.runs.addItem(f'{run.title} · {when or run.folder.name}')
        self.runs.blockSignals(False)
        has = bool(self.run_list)
        for item in (self.runs, self.runs_label, self.line):
            item.setVisible(has)
        self.show_empty(not has)
        if has:
            self.runs.blockSignals(True)
            self.runs.setCurrentIndex(len(self.run_list) - 1)
            self.runs.blockSignals(False)
            self.choose(len(self.run_list) - 1)
        return len(self.run_list)

    def original(self):
        from azimuth import crystal_projects
        from modules.compass.chemistry import crystal as cr

        try:
            return cr.parse_cif(crystal_projects.cif_text(self.manifest))
        except (OSError, ValueError, KeyError):
            return None

    EMPTY_TEXT = ('У этого кристалла ещё нет расчётов. Посчитайте его в Секстанте (CP2K или Quantum ESPRESSO) — '
                  'результаты появятся здесь.')

    def show_empty(self, empty, text=None):
        """No run — the tab «Энергия и шаги» alone, its table empty, Quill and the hint in place of its plots
        (as the first tab of the empty Spectrum of a molecule); a run — its plots back."""
        self.empty.setVisible(bool(empty))
        self.empty_text.setText(text or tr(self.EMPTY_TEXT))
        for item in (self.energy_plot, self.cell_plot):
            item.setVisible(not empty)
        if empty:
            self.steps_table.setRowCount(0)
            for k in range(self.tabs.count()):
                self.tabs.setTabVisible(k, k == self.optimization_tab)
            self.tabs.setCurrentIndex(self.optimization_tab)
        return bool(empty)

    def choose(self, index):
        if not 0 <= index < len(self.run_list):
            return None
        run = self.run = self.run_list[index]
        self.show_line(run)
        self.show_optimization(run)
        self.show_bands(run)
        self.show_charges(run)
        self.show_aim(run)
        visible = [k for k in range(self.tabs.count()) if self.tabs.isTabVisible(k)]
        if visible and not self.tabs.isTabVisible(self.tabs.currentIndex()):
            self.tabs.setCurrentIndex(visible[0])
        return run

    def show_line(self, run):
        import numpy as np

        from modules.compass.chemistry import crystal_results, crystal_steps

        r = crystal_results.result(run)
        if r is None or r.energy is None:
            self.line.setText(tr('{}: расчёт не закончен или его вывода нет.').format(run.folder.name))
            return
        parts = [tr('Полная энергия ячейки: {} Eh = {} эВ').format(f'{r.energy_hartree:.6f}',
                                                                    f'{r.energy_hartree * HARTREE_EV:.4f}')]
        if r.steps:
            parts.append(tr('шагов оптимизации: {}{}').format(r.steps, '' if r.converged else tr(' (не сошлась)')))
        if r.cell is not None:
            lengths = [float(np.linalg.norm(v)) for v in r.cell]
            parts.append(tr('ячейка расчёта: a = {}, b = {}, c = {} Å').format(*(f'{x:.4f}' for x in lengths)))
            original = self.original()
            try:
                raw = crystal_results.steps(run) if original is not None else []
            except (OSError, ValueError, IndexError):
                raw = []
            computed = crystal_steps.guess_computed(original, raw[0][1]) if raw else None
            if computed is not None and computed[0] != (1, 1, 1):
                n = computed[0]
                parts.append(tr('суперячейка {} → ячейка файла a = {}, b = {}, c = {} Å').format(
                    ' × '.join(str(k) for k in n), *(f'{x / k:.4f}' for x, k in zip(lengths, n))))
        self.line.setText(' · '.join(parts))

    def show_optimization(self, run):
        from modules.compass.chemistry import crystal_results

        try:
            raw = crystal_results.steps(run)
        except (OSError, ValueError, IndexError):
            raw = []
        rows = crystal_results.steps_table(raw)
        self.tabs.setTabVisible(self.optimization_tab, True)
        has = len(rows) >= 2
        for item in (self.energy_plot, self.cell_plot):  # the plots of an optimization; an energy — its row only
            item.setVisible(has)
        self.empty.setVisible(not has)
        if len(rows) == 1:  # an energy — its row in the table, Quill says what the plots are for
            self.empty_text.setText(tr('У расчёта энергии один шаг — он в таблице слева. Графики энергии и ячейки по '
                                       'шагам появятся у оптимизации.'))
        if not rows:  # no energy and cell read from the output: Quill says where the result is
            self.steps_table.setRowCount(0)
            self.empty_text.setText(tr('В выводе этого расчёта нет шагов с энергией и ячейкой — итог расчёта в строке '
                                       'внизу.'))
            return
        atoms = max(1, len(raw[-1][2]))
        last = rows[-1]['energy']
        delta = [((row['energy'] - last) * HARTREE_EV * EV_MEV / atoms)
                 if row['energy'] is not None and last is not None else None for row in rows]
        self.energy_plot.series = [(tr('ΔE'), delta)]
        first = rows[0]
        self.cell_plot.series = [(name, [100.0 * (row[key] / first[key] - 1) for row in rows])
                                 for name, key in (('Δa', 'a'), ('Δb', 'b'), ('Δc', 'c'), ('ΔV', 'volume'))]
        _fill(self.steps_table, [(row['step'], f"{row['energy']:.8f}" if row['energy'] is not None else '',
                                  f'{d:.3f}' if d is not None else '', f"{row['a']:.4f}", f"{row['b']:.4f}",
                                  f"{row['c']:.4f}", f"{row['volume']:.3f}") for row, d in zip(rows, delta)])
        self.energy_plot.update()
        self.cell_plot.update()

    def show_bands(self, run):
        from modules.compass.chemistry import crystal_results

        bands = crystal_results.bands(run)
        self.tabs.setTabVisible(self.bands_tab, bands is not None)
        if bands is not None:
            found, path, e0 = bands
            self.bands_plot.x = path['x']
            self.bands_plot.energies = [[e - (e0 or 0.0) for e in row] for row in found.energies]
            self.bands_plot.ticks, self.bands_plot.breaks = [tuple(t) for t in path['ticks']], path['breaks']
            self.bands_plot.update()
        self.show_dos(run)

    def show_dos(self, run):
        """The DOS of dos.x (Quantum ESPRESSO) or of the levels of CP2K, and the PDOS of the run."""
        from modules.compass.chemistry import crystal_results
        from modules.spectrum.readers import cp2k

        dos = crystal_results.dos(run)
        try:
            self.pdos_found = crystal_results.pdos(run)
        except (OSError, ValueError):
            self.pdos_found = None
        wavefunction = run.program == 'cp2k' and bool(cp2k.molden_files(run.folder))
        self.tabs.setTabVisible(self.dos_tab, dos is not None or self.pdos_found is not None or wavefunction)
        self._dos = dos
        self.pdos_button.setVisible(self.pdos_found is None and wavefunction)
        self.projection.setEnabled(self.pdos_found is not None)
        self.draw_dos()

    def draw_dos(self):
        plot, found = self.dos_plot, self.pdos_found
        dos = getattr(self, '_dos', None)
        key = self.projection.currentData()
        notes = []
        if found is not None:
            plot.energies = list(found.x)
            plot.dos = list(found.total)
            plot.parts = [(name, list(y)) for name, y in (found.parts if key == 'elements' else found.orbitals
                                                           if key == 'orbitals' else [])]
            plot.span = (max(float(found.x.min()), -25.0), min(float(found.x.max()), 12.0))
            units = found.extra.get('units')
            plot.label = 'DOS, состояний/эВ на формульную единицу' if units else 'DOS, состояний/эВ'
            source = {'pdos': tr('проекции CP2K (файлы .pdos)'),
                      'molden': tr('доли Малликена орбиталей CP2K (файл Molden, точка Γ, перекрывание с образами ячейки)'),
                      'projwfc': tr('проекции Лёвдина projwfc.x')}.get(found.source, found.source)
            notes.append(tr('PDOS: {}; уширение — гауссиан 0,3 эВ; E₀ — вершина валентной зоны.').format(source))
            if found.note:
                notes.append(tr(found.note))
        elif dos is not None:
            energies, e0 = dos
            plot.energies = [e - (e0 or 0.0) for e in energies.energies]
            plot.dos, plot.parts, plot.label = energies.dos, [], 'DOS, состояний/эВ'
            plot.span = (-12.0, 8.0)
        else:
            plot.energies, plot.dos, plot.parts = [], [], []
            notes.append(tr('Плотность состояний CP2K ещё не считалась: доли атомов в орбиталях — по волновой функции '
                            'расчёта (десятки секунд для суперячейки из 50 атомов).'))
        self.dos_note.setText(' '.join(notes))
        plot.update()

    def compute_pdos(self):
        from azimuth.tasks import run_waiting
        from modules.compass.chemistry import crystal_results

        try:
            run_waiting(self, tr('Плотность состояний по волновой функции…'),
                        lambda step: crystal_results.pdos(self.run, compute=True))
        except InterruptedError:
            return False
        except (OSError, ValueError) as exc:
            self.dos_note.setText(str(exc))
            return False
        self.show_dos(self.run)
        return self.pdos_found is not None

    def show_charges(self, run):
        from modules.compass.chemistry import crystal_results
        from modules.spectrum.wavefunction import crystal_aim

        self.tabs.setTabVisible(self.charges_tab, run.program == 'cp2k')
        if run.program != 'cp2k':
            return
        kept = crystal_results.read_charges(run.folder)
        if kept is None:
            _fill(self.charges_table, [])
            self.charges_note.setText(tr('Заряды ещё не считались. Multiwfn: CM5 и Хиршфельд по волновой функции CP2K '
                                         '(около минуты на 50 атомов).'))
            self.charges_button.setText(tr('Посчитать заряды в Multiwfn'))
            return
        symbols, charges = kept
        _fill(self.charges_table, [(k + 1, s, f"{charges['hirshfeld'][k]:+.4f}", f"{charges['cm5'][k]:+.4f}")
                                   for k, s in enumerate(symbols)])
        summary = crystal_aim.charge_rows([(s, None) for s in symbols], charges)
        self.charges_note.setText((tr('По элементам: ') + '; '.join(
            tr('{}: {} (Хиршфельд), {} (CM5)').format(s, h, c) for s, _n, h, c, _d in summary)).replace('-', '−'))
        self.charges_button.setText(tr('Посчитать заново'))

    def show_aim(self, run):
        from modules.compass.chemistry import crystal_results
        from modules.spectrum.wavefunction import crystal_aim

        self.tabs.setTabVisible(self.aim_tab, run.program == 'cp2k')
        if run.program != 'cp2k':
            return
        kept = crystal_results.read_aim(run.folder)
        if kept is None:
            _fill(self.aim_table, [])
            self.aim_note.setText(tr('Связи ещё не считались. Multiwfn: критические точки плотности, связи по типам '
                                     '(несколько минут на 50 атомов).'))
            self.aim_button.setText(tr('Посчитать связи по AIM в Multiwfn'))
            return
        rows, meta = kept
        _fill(self.aim_table, [tuple(row[:-1]) + (tr(crystal_aim.NATURE.get(row[-1], row[-1])),) for row in rows])
        missing = (meta.get('census') or {}).get('poincare_hopf', 0)
        note = tr('∇²ρ > 0 и H > 0 — замкнутые оболочки (ионная связь, слабый контакт); ∇²ρ < 0 — ковалентная.')
        if missing:
            note += ' ' + tr('Найдены не все точки (ядра − связи + кольца − клетки = {}): связей у атома может быть '
                             'меньше настоящего.').format(missing)
        self.aim_note.setText(note)
        self.aim_button.setText(tr('Посчитать заново'))

    # -- Multiwfn ---------------------------------------------------------------------------------------------------------
    def cores(self):
        cores = getattr(self.window_, 'cores', None)
        return cores.value() if cores is not None else 1

    def compute_charges(self):
        from modules.compass.actions import crystal_analysis

        try:
            crystal_analysis.compute_charges(self, self.run, crystal_analysis.multiwfn_program(self.window_), self.cores())
        except InterruptedError:
            return False
        except (OSError, ValueError) as exc:
            self.charges_note.setText(str(exc))
            return False
        self.show_charges(self.run)
        return True

    def compute_aim(self):
        from modules.compass.actions import crystal_analysis

        try:
            crystal_analysis.compute_aim(self, self.run, crystal_analysis.multiwfn_program(self.window_), self.cores())
        except InterruptedError:
            return False
        except (OSError, ValueError) as exc:
            self.aim_note.setText(str(exc))
            return False
        self.show_aim(self.run)
        return True
