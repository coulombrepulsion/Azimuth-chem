"""«Расчёт» of Compass: a quick xtb, the charge and the multiplicity, the steps as data, the modes of atoms.

§1 PURPOSE
    As the Computation and Job tools menus of Chemcraft. Chemcraft computes with xtb
    from the window of the model; here the same four jobs — energy, optimization, optimization + frequencies, a relaxed
    scan of the selected 2–4 atoms — go from Compass straight to a calculation of Sextant with xtb (GFN2), whatever
    program Sextant shows, with the charge and multiplicity of the tab; the result comes back like any other. The
    steps of a result: one XYZ, a table of all coordinates, a parameter or the angle of two guides along the steps.
    The normal modes ranked by the share of the selected atoms in the motion.
§2 ALGORITHM
    quick_xtb(task, scan=None): Calculation(task, charge, multiplicity, cores, solvent of the form; xtb ignores the
    method and the basis); a scan: the selected atoms make the coordinate (2 — bond, 3 — angle, 4 — dihedral), the
    frozen atoms of the tab stay; runner.prepare('xtb', …) and Job, then job_started (the job window, the history, the
    project). The data of the steps and modes: modules/compass/chemistry/step_tools.py.
§4 SPECIFICATION QUICK_TASKS; CalculationTool (window.calculation_tool; was the mixin CalculationTools):
    build_calculation_tools() -> {key: QAction} and the menus 'quick_xtb', 'steps_data'; quick_xtb(task, scan=None) ->
    Job | None (scan = (end, points)); quick_scan_dialog(); set_charge_and_multiplicity(charge=None, multiplicity=None)
    -> (q, 2S + 1) | None; save_steps_xyz(path=None); save_steps_table(path=None); parameter_plot(atoms=None,
    guides=None) -> ParameterPlot | None; modes_of_selected()
    -> text | None.
§7 TESTS
    tests/compass/test_step_tools.py (the data); tests/gui/test_gui_compass.py::test_calculation_menu_of_compass.
"""

from dataclasses import replace

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (QDialog, QDialogButtonBox, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel,
                               QMenu, QPushButton, QSpinBox, QVBoxLayout, QWidget)

from azimuth.core import SCAN_TASK, SCAN_UNITS, coordinate_value
from azimuth.i18n import tr
from azimuth.ui import smooth

QUICK_TASKS = (('Энергия', 'Энергия'), ('Оптимизация', 'Оптимизация'), ('Оптимизация + частоты', 'Оптимизация + частоты'))
KINDS = {2: 'B', 3: 'A', 4: 'D'}


class ParameterPlot(QDialog):
    """A value along the steps: a line with dots, the step on x; the energy (ΔE) on the right axis when known."""

    def __init__(self, owner, title, unit, series):
        super().__init__(owner)
        self.setWindowTitle(title)
        self.series, self.unit = series, unit
        lay = QVBoxLayout(self)
        self.canvas = _Canvas(series, unit)
        lay.addWidget(self.canvas, 1)
        row = QHBoxLayout()
        save = QPushButton(tr('Сохранить CSV…'))
        save.clicked.connect(lambda: self.save_csv())
        close = QPushButton(tr('Закрыть'))
        close.clicked.connect(self.accept)
        row.addWidget(save)
        row.addStretch(1)
        row.addWidget(close)
        lay.addLayout(row)
        self.resize(560, 380)

    def save_csv(self, path=None):
        from azimuth import defaults
        from modules.spectrum.wavefunction import field_tables

        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить таблицу'), 'steps_parameter.csv', 'CSV (*.csv)')
            if not path:
                return None
        energies = [e for _, _, e in self.series if e is not None]
        low = min(energies) if energies else None
        rows = [(n, f'{v:.6f}', '' if e is None else f'{(e - low) * defaults.energy_factor():.4f}')
                for n, v, e in self.series]
        return field_tables.write_csv(path, [tr('Шаг'), self.unit, 'ΔE, ' + tr(defaults.energy_name())], rows)


class _Canvas(QWidget):
    def __init__(self, series, unit):
        super().__init__()
        self.series, self.unit = series, unit
        self.setMinimumSize(420, 260)

    def paintEvent(self, event):
        if not self.series:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = self.palette().text().color()
        font = QFont(self.font())
        font.setPixelSize(10)
        p.setFont(font)
        left, right, top, bottom = 60, self.width() - 60, 14, self.height() - 30
        steps = [n for n, _, _ in self.series]
        values = [v for _, v, _ in self.series]
        lo, hi = min(values), max(values)
        if hi - lo < 1e-9:
            lo, hi = lo - 0.5, hi + 0.5
        s0, s1 = min(steps), max(steps) if max(steps) > min(steps) else min(steps) + 1

        def x(n):
            return left + (n - s0) / (s1 - s0) * (right - left)

        def y(v, a=lo, b=hi):
            return bottom - (v - a) / (b - a) * (bottom - top)

        p.setPen(QPen(ink, 1))
        p.drawLine(QPointF(left, bottom), QPointF(right, bottom))
        p.drawLine(QPointF(left, top), QPointF(left, bottom))
        for v in (lo, hi):
            p.drawText(QRectF(0, y(v) - 7, left - 6, 14), Qt.AlignmentFlag.AlignRight, f'{v:.3f}')
        p.drawText(QRectF(left, bottom + 6, right - left, 14), Qt.AlignmentFlag.AlignCenter, tr('Шаг'))
        p.drawText(QRectF(4, top - 12, 120, 12), Qt.AlignmentFlag.AlignLeft, self.unit)
        energies = [(n, e) for n, _, e in self.series if e is not None]
        if len(energies) > 1:  # the energy, grey, scaled on its own
            elo, ehi = min(e for _, e in energies), max(e for _, e in energies)
            if ehi - elo > 1e-12:
                p.setPen(QPen(QColor('#9aa8b8'), 1.2, Qt.PenStyle.DashLine))
                for (n1, e1), (n2, e2) in zip(energies, energies[1:]):
                    p.drawLine(QPointF(x(n1), y(e1, elo, ehi)), QPointF(x(n2), y(e2, elo, ehi)))
                p.drawText(QRectF(right + 4, top - 2, 56, 12), Qt.AlignmentFlag.AlignLeft, 'E')
        blue = QColor('#2a62b8')
        p.setPen(QPen(blue, 2))
        for (n1, v1, _), (n2, v2, _) in zip(self.series, self.series[1:]):
            p.drawLine(QPointF(x(n1), y(v1)), QPointF(x(n2), y(v2)))
        p.setBrush(blue)
        for n, v, _ in self.series:
            p.drawEllipse(QPointF(x(n), y(v)), 3, 3)
        p.end()


class CalculationTool:
    """Was the mixin CalculationTools of the window; a part of its own — it reaches the window only through
    the names of PORT (azimuth/window_port.WindowPort)."""

    PORT = (
        'calc_tool_actions',
        'calc_tool_menus',
        'calculation',
        'calculation_constraints',
        'calculation_molecule',
        'charge',
        'coordinate_tool',
        'drawer',
        'error',
        'job_window',
        'molecule',
        'notify',
        'run_tool',
        'stack',
        'spin',
        'structure_tool',
        'viewer',
    )

    def __init__(self, window):
        from azimuth.window_port import WindowPort

        self.w = WindowPort(window, self.PORT)


    def build_calculation_tools(self):
        acts, menus = {}, {}

        def make(key, title, callback, tip=None):
            item = QAction(tr(title), self.w.widget)
            item.triggered.connect(lambda checked=False: callback())
            if tip:
                item.setToolTip(tr(tip))
            acts[key] = item
            return item

        quick = smooth(QMenu(tr('Быстрый расчёт xtb'), self.w.widget))
        quick.setToolTipsVisible(True)
        for key, title in QUICK_TASKS:
            quick.addAction(make('xtb_' + key, title + ' (xtb)', lambda t=key: self.quick_xtb(t),
                                 'GFN2-xTB с зарядом и мультиплетностью вкладки — сразу, без Секстанта'))
        quick.addAction(make('xtb_gfnff', 'Оптимизация GFN-FF (xtb)', lambda: self.quick_xtb('Оптимизация', 'gfnff'),
                             'Силовое поле GFN-FF Гримме (xtb --gfnff): быстро и для больших молекул, грубее GFN2-xTB'))
        quick.addAction(make('xtb_scan', 'Скан по выделенным атомам (xtb)…', self.quick_scan_dialog,
                             'Выделите 2, 3 или 4 атома: длина, угол или двугранный угол меняется, остальное '
                             'оптимизируется'))
        menus['quick_xtb'] = quick
        make('charge', 'Заряд и мультиплетность…', lambda: self.set_charge_and_multiplicity())
        steps = smooth(QMenu(tr('Шаги расчёта'), self.w.widget))
        steps.setToolTipsVisible(True)
        for key, title, callback, tip in (
                ('steps_xyz', 'Сохранить шаги одним XYZ…', lambda: self.save_steps_xyz(), None),
                ('steps_table', 'Координаты всех шагов (CSV)…', lambda: self.save_steps_table(), None),
                ('steps_plot', 'График параметра по шагам…', lambda: self.parameter_plot(),
                 'Выделите 2–4 атома (длина, угол, двугранный угол) — или задайте два вектора или плоскости в «Правка → '
                 'Векторы и плоскости»: будет угол между ними')):
            steps.addAction(make(key, title, callback, tip))
        menus['steps_data'] = steps
        make('modes_of_atoms', 'Моды с участием выделенных атомов…', lambda: self.modes_of_selected(),
             'Колебания, в которых выделенные атомы двигаются больше всего')
        self.w.calc_tool_actions, self.w.calc_tool_menus = acts, menus
        return acts

    # -- the quick xtb ---------------------------------------------------------------------------------------------
    def quick_xtb(self, task, method=None, scan=None):
        """A calculation of xtb from Compass: task one of QUICK_TASKS or SCAN_TASK with scan = (end, points) of the
        coordinate of the selected atoms. → the Job, or None (the reason said)."""
        from modules.sextant import runner

        if self.w.run_tool.job_running():
            self.w.notify(tr('Расчёт уже идёт: дождитесь его конца или остановите.'), 6000)
            return None
        program = runner.find_program('xtb', self.w.run_tool.configured_program('xtb'))
        if program is None:
            self.w.error(ValueError(tr('xtb не найдена: «Расчёт → Установить программы для расчёта…» в Секстанте или '
                                     '«Файл → Настройки → Программы».')))
            return None
        form = self.w.calculation()
        calc = replace(form, task=task, dispersion='', relativistic='', ts=False, extra='', orbitals=False,
                       calc_hessian=False, num_freq=False, title='')
        if method:  # 'gfnff' — Calculation.xtb_method (the method of the form stays: it is validated)
            calc = replace(calc, xtb_method=method)
        constraints = tuple(self.w.calculation_constraints())
        if scan is not None:
            atoms = tuple(self.w.viewer.selected)
            if len(atoms) not in KINDS:
                self.w.error(ValueError(tr('Для скана выделите 2, 3 или 4 атома.')))
                return None
            frozen = tuple(c for c in constraints if c[0] == 'C')
            constraints = ((KINDS[len(atoms)], atoms),) + frozen
            calc = replace(calc, task=SCAN_TASK, scan_index=0, scan_end=float(scan[0]), scan_steps=int(scan[1]))
        try:
            spec = runner.prepare('xtb', program, self.w.calculation_molecule(), calc, constraints, self.w.run_tool.jobs_root())
            job = runner.Job(spec).start()
        except (ValueError, OSError) as exc:
            self.w.error(exc)
            return None
        # its sign in the panel of the hub is the compass (hub/job_indicator.py)
        try:
            job.section = 'compass'
            job.follow = lambda what: self.follow_quick(job, what)  # no window — the pill (RunTool.job_started)
        except AttributeError:
            pass
        return self.w.run_tool.job_started(job, calc, 'xtb', None)

    def follow_quick(self, job, what):
        """The quick xtb on the pill over the model — what, the time, «Esc — остановить», the
        turning compass; in another section the window of the calculation stays hidden and the sign of the left panel
        tells it (parked); at the end a line of how it went."""
        import time

        from PySide6.QtCore import QEvent, QObject, Qt, QTimer
        from PySide6.QtWidgets import QApplication

        from azimuth import tasks

        window = self.w.widget
        started = time.monotonic()
        hint = tr('Esc — остановить')

        class Esc(QObject):
            def eventFilter(self_, obj, event):
                try:
                    if event.type() == QEvent.Type.KeyPress and event.key() == Qt.Key.Key_Escape \
                            and QApplication.activePopupWidget() is None and QApplication.activeModalWidget() is None \
                            and self.w.stack.currentIndex() == 0 and job.running:
                        self.w.run_tool.stop_calculation()
                        return True
                except RuntimeError:  # the window is gone — the filter goes too
                    app = QApplication.instance()
                    if app is not None:
                        app.removeEventFilter(self_)
                return False

        esc = Esc()
        app = QApplication.instance()
        timer = QTimer(window)
        timer.setInterval(500)

        def tick():
            here = self.w.stack.currentIndex() == 0
            try:
                self.w.job_window._set_parked(not here)
            except AttributeError:
                pass
            if job.running:
                if here:
                    spent = int(time.monotonic() - started)
                    tasks.pill_busy(window, f'xtb · {what} · {spent // 60}:{spent % 60:02d} · {hint}')
                return
            timer.stop()
            app.removeEventFilter(esc)
            tasks.pill_busy(window, '', on=False)
            if here:
                self.w.job_window._set_parked(False)
            done = job.code == 0
            self.w.notify(tr('Быстрый расчёт xtb закончен.') if done else
                          tr('Быстрый расчёт xtb не закончен — подробности в Секстанте («Вывод программы»).'), 8000)

        app.installEventFilter(esc)
        timer.timeout.connect(tick)
        self._quick = (timer, esc)  # kept while it runs
        timer.start()
        tick()
        return timer

    def quick_scan_dialog(self, values=None):
        """The end value and the points of a quick scan; values = (end, points) without the window (the tests)."""
        atoms = tuple(self.w.viewer.selected)
        if len(atoms) not in KINDS:
            self.w.notify(tr('Выделите 2, 3 или 4 атома: длина, угол или двугранный угол.'), 6000)
            return None
        kind = KINDS[len(atoms)]
        now = coordinate_value(self.w.coordinate_tool.table_molecule(), kind, atoms)
        if values is not None:
            return self.quick_xtb(SCAN_TASK, scan=values)
        box = QDialog(self.w.widget)
        box.setWindowTitle(tr('Скан xtb'))
        form = QFormLayout(box)
        unit = SCAN_UNITS[kind]
        names = {'B': 'Длина', 'A': 'Угол', 'D': 'Двугранный угол'}
        label = '–'.join(f'{self.w.molecule.atoms[i].symbol}{i + 1}' for i in atoms)
        form.addRow(QLabel(tr(names[kind]) + f' {label}: ' + f'{now:.{3 if kind == "B" else 1}f} {unit}'))
        end = QDoubleSpinBox()
        end.setDecimals(3 if kind == 'B' else 1)
        end.setRange(*{'B': (0.3, 10.0), 'A': (1.0, 179.0), 'D': (-360.0, 360.0)}[kind])
        end.setSuffix(' ' + unit)
        end.setValue(min(end.maximum(), now + (0.5 if kind == 'B' else 30.0)))
        points = QSpinBox()
        points.setRange(3, 100)
        points.setValue(11)
        form.addRow(tr('Конец'), end)
        form.addRow(tr('Точек'), points)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.rejected.connect(box.reject)

        def accept():
            box.accept()
            self.quick_xtb(SCAN_TASK, scan=(end.value(), points.value()))

        buttons.accepted.connect(accept)
        self._scan_box = box
        from azimuth.ui import open_window

        open_window(box)  # a window with its title, not a sheet
        return None

    def set_charge_and_multiplicity(self, charge=None, multiplicity=None):
        """The charge and the multiplicity of the tab — the fields of Sextant — from Compass."""
        if charge is not None or multiplicity is not None:
            if charge is not None:
                self.w.charge.setValue(int(charge))
            if multiplicity is not None:
                self.w.spin.setValue(int(multiplicity))
            return self.w.charge.value(), self.w.spin.value()
        box = QDialog(self.w.widget)
        box.setWindowTitle(tr('Заряд и мультиплетность'))
        form = QFormLayout(box)
        q, m = QSpinBox(), QSpinBox()
        q.setRange(self.w.charge.minimum(), self.w.charge.maximum())
        m.setRange(self.w.spin.minimum(), self.w.spin.maximum())
        q.setValue(self.w.charge.value())
        m.setValue(self.w.spin.value())
        form.addRow(tr('Заряд'), q)
        form.addRow(tr('Мультиплетность 2S + 1'), m)
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        form.addRow(buttons)
        buttons.rejected.connect(box.reject)

        def accept():
            box.accept()
            self.set_charge_and_multiplicity(q.value(), m.value())

        buttons.accepted.connect(accept)
        self._charge_box = box
        from azimuth.ui import open_window

        open_window(box)  # a window with its title, not a sheet
        return None

    # -- the steps of a result ------------------------------------------------------------------------------------
    def _result_steps(self):
        steps = tuple(getattr(self.w.drawer, 'steps', ()) or ())
        if not any(getattr(s, 'geometry', None) is not None for s in steps):
            self.w.notify(tr('Во вкладке нет шагов расчёта: откройте результат оптимизации, скана или IRC.'), 6000)
            return None
        return steps

    def save_steps_xyz(self, path=None):
        from modules.compass.chemistry import step_tools

        steps = self._result_steps()
        if steps is None:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self.w.widget, tr('Шаги одним XYZ'), 'steps.xyz', 'XYZ (*.xyz)')
            if not path:
                return None
        from pathlib import Path

        Path(path).write_text(step_tools.steps_xyz(steps), encoding='utf-8')
        self.w.notify(tr('Сохранено: ') + str(path), 6000)
        return path

    def save_steps_table(self, path=None):
        from modules.compass.chemistry import step_tools
        from modules.spectrum.wavefunction import field_tables

        steps = self._result_steps()
        if steps is None:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self.w.widget, tr('Координаты всех шагов'), 'steps_coordinates.csv',
                                                  'CSV (*.csv)')
            if not path:
                return None
        rows = [(n, i, s, f'{x:.6f}', f'{y:.6f}', f'{z:.6f}') for n, i, s, x, y, z in step_tools.coordinate_rows(steps)]
        return field_tables.write_csv(path, [tr('Шаг'), tr('Атом'), tr('Элемент'), 'X, Å', 'Y, Å', 'Z, Å'], rows)

    def parameter_plot(self, atoms=None, guides=None):
        """The selected 2–4 atoms (or the first two vectors / planes of the model) along the steps of the result."""
        from modules.compass.chemistry import step_tools

        steps = self._result_steps()
        if steps is None:
            return None
        atoms = tuple(self.w.viewer.selected) if atoms is None else tuple(atoms)
        made = list(getattr(self.w.viewer, 'guides', []) or [])
        guides = guides if guides is not None else (made[:2] if len(atoms) not in KINDS and len(made) >= 2 else None)
        try:
            if guides:
                series = step_tools.guide_series(steps, guides[0], guides[1])
                title, unit = tr('Угол между векторами и плоскостями 1 и 2 по шагам'), tr('угол, °')
            else:
                series = step_tools.parameter_series(steps, atoms)
                kind = KINDS[len(atoms)]
                symbols = [a.symbol for a in self.w.molecule.atoms]
                name = '–'.join(f'{symbols[i]}{i + 1}' if i < len(symbols) else str(i + 1) for i in atoms)
                title = {'B': tr('Длина'), 'A': tr('Угол'), 'D': tr('Двугранный угол')}[kind] + f' {name} ' + tr('по шагам')
                unit = {'B': 'r, Å', 'A': '∠, °', 'D': 'φ, °'}[kind]
        except ValueError as exc:
            self.w.notify(tr(str(exc)), 8000)
            return None
        plot = ParameterPlot(self.w.widget, title, unit, series)
        self.parameter_window = plot
        plot.show()
        return plot

    def modes_of_selected(self):
        """The modes of the result ranked by the share of the selected atoms in their motion."""
        from modules.compass.chemistry import step_tools

        modes = tuple(getattr(self.w.drawer, 'modes', ()) or ())
        if not modes:
            self.w.notify(tr('Во вкладке нет частот: откройте расчёт частот.'), 6000)
            return None
        chosen = list(self.w.viewer.selected)
        if not chosen:
            self.w.notify(tr('Выделите атомы, движение которых ищете.'), 6000)
            return None
        try:
            found = step_tools.involvement(modes, chosen)
        except ValueError as exc:
            self.w.notify(tr(str(exc)), 6000)
            return None
        symbols = [a.symbol for a in self.w.molecule.atoms]
        names = ', '.join(f'{symbols[i]}{i + 1}' for i in chosen if i < len(symbols))
        lines = [tr('Доля выделенных атомов в смещениях моды (сумма квадратов их смещений к сумме всех): ') + names, '']
        for index, frequency, share in found[:20]:
            freq = f'{abs(frequency):.1f}i' if frequency < 0 else f'{frequency:.1f}'
            lines.append(f'{tr("Мода")} {index:>3}   {freq:>9} {tr("см⁻¹")}   {100 * share:5.1f} %')
        text = '\n'.join(lines)
        self.w.structure_tool._report(tr('Моды с участием выделенных атомов'), text)
        return text
