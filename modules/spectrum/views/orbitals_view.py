"""The orbital window of the Spectrum module: molecular orbitals of a Molden file, a Gaussian
.fchk or an ORCA output (print[p_mos]).

A table of the orbitals (number, spin, symmetry, energy in hartree and eV, occupation, ВЗМО/НСМО), an
energy-level diagram (occupied levels dark, empty light; a click selects), and the buttons that build a
CUBE field on a grid — the selected orbital, the electron density or the spin density — and show it in
the 3D window of CUBE files, or save it as a .cube file. The numbers come from orbitals.py and
orbital_files.py.
"""

from pathlib import Path

from PySide6.QtCore import QPointF, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from modules.spectrum.analysis.orbitals import write_cube
from azimuth.i18n import tr
from azimuth import quill  # the messages with Quill

HARTREE_EV = 27.211386245988  # CODATA 2018
STEPS = ((0.25, 'Грубая сетка · 0,25 Å'), (0.15, 'Обычная сетка · 0,15 Å'), (0.10, 'Точная сетка · 0,10 Å'))


def frontier_labels(orbital_set):
    """{index: 'ВЗМО', 'ВЗМО−1', 'НСМО', 'НСМО+1', ...} (per spin), translated."""
    labels = {}
    for spin in ('alpha', 'beta'):
        own = sorted(
            (k for k, o in enumerate(orbital_set.orbitals) if o.spin == spin),
            key=lambda k: orbital_set.orbitals[k].energy,
        )
        homo, lumo = orbital_set.frontier(spin)
        if homo is not None:
            h = own.index(homo)
            for shift in range(0, min(h, 4) + 1):
                labels[own[h - shift]] = tr('ВЗМО') + (f'−{shift}' if shift else '')
        if lumo is not None:
            u = own.index(lumo)
            for shift in range(0, min(len(own) - 1 - u, 4) + 1):
                labels[own[u + shift]] = tr('НСМО') + (f'+{shift}' if shift else '')
    return labels


class LevelDiagram(QWidget):
    """Orbital energies (eV) as horizontal lines; alpha and beta side by side for open shells."""

    picked = Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(170, 300)
        self.orbitals = ()
        self.current = None
        self.window_ev = (-20.0, 5.0)
        self.setToolTip(tr('Уровни энергии орбиталей: тёмные — занятые, светлые — свободные. Щелчок выбирает.'))

    def load(self, orbital_set):
        self.orbitals = orbital_set.orbitals
        homo, lumo = orbital_set.frontier('alpha')
        centre = 0.0
        if homo is not None and lumo is not None:
            centre = (self.orbitals[homo].energy + self.orbitals[lumo].energy) / 2 * HARTREE_EV
        elif homo is not None:
            centre = self.orbitals[homo].energy * HARTREE_EV
        self.window_ev = (centre - 15.0, centre + 10.0)
        self.update()

    def _geometry(self):
        top, bottom = 18, self.height() - 22
        low, high = self.window_ev
        columns = 2 if any(o.spin == 'beta' for o in self.orbitals) else 1
        width = (self.width() - 60) / columns
        return top, bottom, low, high, columns, width

    def _y(self, energy_ev):
        top, bottom, low, high, _, _ = self._geometry()
        return bottom - (energy_ev - low) / (high - low) * (bottom - top)

    def _x(self, orbital):
        _, _, _, _, columns, width = self._geometry()
        column = 1 if orbital.spin == 'beta' and columns == 2 else 0
        return 50 + column * width + 6, 50 + (column + 1) * width - 6

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self.palette().window().color().lightness() < 110
        text = QColor('#d8dee8' if dark else '#33404d')
        p.setPen(QPen(text, 1))
        top, bottom, low, high, columns, width = self._geometry()
        p.drawLine(46, top, 46, bottom)
        step = 5
        value = int(low // step + 1) * step
        while value <= high:
            y = self._y(value)
            p.drawLine(42, int(y), 46, int(y))
            p.drawText(QPointF(4, y + 4), f'{value:g}')
            value += step
        p.drawText(QPointF(4, top - 5), tr('E, эВ'))
        if columns == 2:
            p.drawText(QPointF(50 + width / 2 - 4, bottom + 16), 'α')
            p.drawText(QPointF(50 + 1.5 * width - 4, bottom + 16), 'β')
        for k, o in enumerate(self.orbitals):
            e = o.energy * HARTREE_EV
            if not low <= e <= high:
                continue
            x0, x1 = self._x(o)
            y = self._y(e)
            occupied = o.occupation > 1e-6
            color = QColor('#2a62b8') if occupied else QColor('#9aa8b8')
            p.setPen(QPen(QColor('#e0503c') if k == self.current else color, 3 if k == self.current else 2))
            p.drawLine(QPointF(x0, y), QPointF(x1, y))

    def mousePressEvent(self, event):
        best = None
        point = event.position()
        for k, o in enumerate(self.orbitals):
            x0, x1 = self._x(o)
            if not x0 - 4 <= point.x() <= x1 + 4:
                continue
            d = abs(self._y(o.energy * HARTREE_EV) - point.y())
            if d < 6 and (best is None or d < best[0]):
                best = (d, k)
        if best is not None:
            self.picked.emit(best[1])

    def wheelEvent(self, event):
        low, high = self.window_ev
        shift = (high - low) * 0.1 * (1 if event.angleDelta().y() > 0 else -1)
        self.window_ev = (low + shift, high + shift)
        self.update()


class OrbitalsDialog(QDialog):
    """show_cube(cube, density: bool) is called with every field built here."""

    def __init__(self, orbital_set, source, show_cube, parent=None, show_in_compass=None, show_aim=None, to_compass=None):
        super().__init__(parent)
        # (orbital_set, source, tab, state) -> the density panel of Compass takes the work over after a field
        # is put on the model; the window hides
        self.to_compass = to_compass
        self.show_in_compass = show_in_compass  # (cube, kind, orbital_set, title) -> bool
        self.show_aim = show_aim  # (topology, orbital_set, title) -> bool — QTAIM on the Compass model
        self.density_dialog = None
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setWindowTitle(tr('Азимут · Орбитали · ') + source)
        self.resize(900, 620)
        self.orbital_set = orbital_set
        self.show_cube = show_cube
        self.source = source
        layout = QVBoxLayout(self)
        nbasis = sum(s.size for s in orbital_set.shells)
        if getattr(orbital_set, 'zdo', False):  # MOPAC — Slater functions, NDDO orthonormality
            checked = (tr(f'перекрывания совпадают с MOPAC с точностью {orbital_set.deviation:.0e}')
                       if orbital_set.deviation == orbital_set.deviation else tr('перекрывания MOPAC не записаны'))
            text = tr(f'{orbital_set.title or source} · базис: {nbasis} слэтеровских функций (каждая как '
                      f'{orbital_set.convention.split()[-2]} гауссовых) · орбиталей: {len(orbital_set.orbitals)} · ') + checked + tr(
                ' · NDDO: C^T C = 1')
        else:
            text = tr(
                f'{orbital_set.title or source} · базис: {nbasis} функций · орбиталей: {len(orbital_set.orbitals)} · '
                f'нормировка: {orbital_set.convention} (C^T S C = 1 с точностью {orbital_set.deviation:.0e})'
            )
        self.info = QLabel(text)
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        row = QHBoxLayout()
        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            [tr('№'), tr('Спин'), tr('Симметрия'), tr('E, хартри'), tr('E, эВ'), tr('Заселённость'), '']
        )
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        row.addWidget(self.table, 3)
        self.levels = LevelDiagram()
        row.addWidget(self.levels, 1)
        layout.addLayout(row, 1)
        bar = QHBoxLayout()
        self.step = QComboBox()
        for value, title in STEPS:
            self.step.addItem(tr(title), value)
        self.step.setCurrentIndex(1)
        self.step.setToolTip(tr('Шаг сетки; запас вокруг молекулы — 4 Å. Более мелкая сетка точнее, но дольше.'))
        bar.addWidget(self.step)
        self.target = QComboBox()  # where the field is shown
        self.target.addItem(tr('в окне 3D'), 'window')
        if show_in_compass is not None:
            self.target.addItem(tr('на модели Компаса'), 'compass')
            self.target.setCurrentIndex(1)
        self.target.setToolTip(tr('Где показать поверхность: в отдельном окне или прямо на модели Компаса'))
        bar.addWidget(self.target)
        bar.addStretch()
        self.orbital_button = QPushButton(tr('Показать орбиталь'))
        self.orbital_button.setObjectName('primary')
        self.density_button = QPushButton(tr('Электронная плотность'))
        self.spin_button = QPushButton(tr('Спиновая плотность'))
        self.spin_button.setEnabled(orbital_set.unrestricted)
        self.esp_button = QPushButton(tr('ESP на поверхности'))  # the ESP of the wavefunction, from Multiwfn
        self.multiwfn = None  # set_multiwfn: (source() -> (program, file, cores) | None, esp() -> bool)
        self.multiwfn_esp = None
        self.esp_button.setVisible(False)
        self.analysis_button = QPushButton(tr('Анализ ЭП…'))  # modules/spectrum/views/density_view.py
        self.analysis_button.setToolTip(
            tr('Электронная плотность: лапласиан, разность плотностей, критические точки и пути связей (QTAIM), срез')
        )
        self.save_button = QPushButton(tr('Сохранить CUBE…'))
        self.save_button.setToolTip(tr('Сохранить выбранную орбиталь в файл CUBE (координаты в борах)'))
        for b in (self.orbital_button, self.density_button, self.spin_button, self.esp_button, self.analysis_button,
                  self.save_button):
            bar.addWidget(b)
        layout.addLayout(bar)
        self.status = QLabel(tr('Двойной щелчок по строке или уровню показывает орбиталь.'))
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        self.fill()
        self.table.itemSelectionChanged.connect(self.selection_changed)
        self.table.cellDoubleClicked.connect(lambda *a: self.show_orbital())
        self.levels.picked.connect(self.select)
        self.orbital_button.clicked.connect(self.show_orbital)
        self.density_button.clicked.connect(lambda: self.show_density(False))
        self.spin_button.clicked.connect(lambda: self.show_density(True))
        self.esp_button.clicked.connect(self.show_esp)
        self.save_button.clicked.connect(self.save_cube)
        self.analysis_button.clicked.connect(self.density_analysis)

    def set_multiwfn(self, source, esp):
        """These orbitals were read from a file Multiwfn can take: the ESP (esp() puts it on the Compass model)
        and the critical points of the analysis window are Multiwfn's."""
        self.multiwfn, self.multiwfn_esp = source, esp
        self.esp_button.setVisible(esp is not None and self.show_in_compass is not None)
        self.esp_button.setToolTip(tr('ESP волновой функции на поверхности ρ = 0,001 с минимумами и максимумами — на модели Компаса'))
        if self.density_dialog is not None:
            self.density_dialog.set_multiwfn(source)

    def show_esp(self):
        if self.multiwfn_esp is None or not self.multiwfn_esp():
            return False
        self.hand_over(0)
        return True

    def density_analysis(self):
        """The window «Анализ электронной плотности» for these orbitals (one; shown again if open)."""
        from modules.spectrum.views.density_view import DensityDialog

        if self.density_dialog is None:
            self.density_dialog = DensityDialog(
                self.orbital_set, self.source, self.show_cube, self.show_in_compass, self.show_aim, self,
                to_compass=(lambda: self.hand_over(self.density_dialog.compass_tab())) if self.to_compass else None,
            )
            self.density_dialog.destroyed.connect(lambda *a: setattr(self, 'density_dialog', None))
            self.density_dialog.set_multiwfn(self.multiwfn)
            # «Убрать с модели» of the points — the host takes them off its model
            self.density_dialog.clear_aim = getattr(self, 'clear_aim', None)
            self.density_dialog.aim_shown = getattr(self, 'aim_shown', None)
            self.density_dialog.keep_contacts = getattr(self, 'keep_contacts', None)
        self.density_dialog.show()
        self.density_dialog.raise_()
        return self.density_dialog

    def hand_over(self, tab=0):
        """The field is on the model — the window gives way to the density panel of Compass (the same
        orbitals, the fragments and critical points of the analysis window)."""
        if self.to_compass is None:
            return False
        state = None
        if self.density_dialog is not None:
            state = self.density_dialog.handover_state()
            self.density_dialog.hide()
        self.hide()
        self.to_compass(self.orbital_set, self.source, tab, state)
        return True

    def fill(self):
        labels = frontier_labels(self.orbital_set)
        orbitals = self.orbital_set.orbitals
        self.table.setRowCount(len(orbitals))
        for k, o in enumerate(orbitals):
            cells = [
                str(o.number),
                'α' if o.spin == 'alpha' else 'β',
                o.symmetry,
                f'{o.energy:.6f}',
                f'{o.energy * HARTREE_EV:.3f}',
                f'{o.occupation:g}',
                labels.get(k, ''),
            ]
            for column, value in enumerate(cells):
                item = QTableWidgetItem(value)
                if column != 2 and column != 6:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(k, column, item)
        self.levels.load(self.orbital_set)
        homo, _ = self.orbital_set.frontier('alpha')
        if homo is not None:
            self.select(homo)

    def select(self, index):
        self.table.selectRow(index)
        self.table.scrollToItem(self.table.item(index, 0))

    def current(self):
        rows = self.table.selectionModel().selectedRows()
        return rows[0].row() if rows else None

    def selection_changed(self):
        self.levels.current = self.current()
        self.levels.update()

    def _busy(self, work, title=None, total=0):
        """Work(step) in a worker thread, the window painting meanwhile (azimuth.tasks.run_waiting)."""
        from azimuth.tasks import run_waiting

        try:
            return run_waiting(self, title or tr('Орбиталь…'), work, total)
        except InterruptedError:  # «Отмена» while Multiwfn computes the grid
            return None
        except (ValueError, MemoryError) as exc:
            quill.warning(self, tr('Орбитали'), str(exc))
            return None

    def orbital_field(self):
        """The field of the chosen orbital; the last one is kept — showing it and saving it as CUBE with the
        same orbital and grid compute it once (orbital set, index, grid step are the key)."""
        index = self.current()
        if index is None:
            self.status.setText(tr('Выберите орбиталь в таблице.'))
            return None
        grid = self.step.currentData()
        key = (id(self.orbital_set), index, grid)
        kept = getattr(self, '_field', None)
        if kept is not None and kept[0] == key:
            return kept[1]
        from modules.spectrum.wavefunction import multiwfn

        quiet = self.grid_source() if getattr(self, 'grid_source', None) else None  # Multiwfn, else ours
        cube = self._busy(lambda step: multiwfn.field_cube(quiet, self.orbital_set, 'orbital', index, grid, progress=step))
        if cube is not None:
            self._field = (key, cube)
        return cube

    def show_orbital(self):
        cube = self.orbital_field()
        if cube is not None:
            o = self.orbital_set.orbitals[self.current()]
            self.status.setText(
                tr(
                    f'Орбиталь {o.number} ({"α" if o.spin == "alpha" else "β"}): сетка {" × ".join(map(str, cube.values.shape[:3]))}.'
                )
            )
            if self.in_compass():
                self.show_in_compass(cube, 'orbital', self.orbital_set, tr(f'Орбиталь {o.number}') + ('' if o.spin == 'alpha' else ' β'))
                self.hand_over(0)
            else:
                self.show_cube(cube, False)

    def in_compass(self):
        return self.show_in_compass is not None and self.target.currentData() == 'compass'

    def show_density(self, spin):
        used = self.orbital_set.occupied()[1]  # with the orbitals the file did not list
        grid = self.step.currentData()
        from modules.spectrum.wavefunction import multiwfn

        quiet = self.grid_source() if getattr(self, 'grid_source', None) else None
        try:
            cube = self._busy(lambda step: multiwfn.field_cube(quiet, self.orbital_set, 'density', None, grid, spin,
                                                               progress=step), tr('Плотность: орбитали…'), len(used))
        except InterruptedError:
            cube = None
        if cube is None:
            return
        if self.in_compass():
            self.show_in_compass(cube, 'spin' if spin else 'density', self.orbital_set,
                                 tr('Спиновая плотность') if spin else tr('Электронная плотность'))
            self.hand_over(0)
        else:
            self.show_cube(cube, True)

    def save_cube(self):
        cube = self.orbital_field()
        if cube is None:
            return
        o = self.orbital_set.orbitals[self.current()]
        name = f'{Path(self.source).stem}-MO{o.number}{"" if o.spin == "alpha" else "b"}.cube'
        path, _ = QFileDialog.getSaveFileName(
            self, tr('Сохранить CUBE'), str(Path.home() / name), tr('CUBE (*.cube *.cub)')
        )
        if path:
            try:
                write_cube(cube, path)
                self.status.setText(tr('Сохранено: ') + path)
            except OSError as exc:
                quill.warning(self, tr('Сохранение'), str(exc))
