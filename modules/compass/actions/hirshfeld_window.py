"""«Кристалл → Поверхность Хиршфельда…»: the Hirshfeld surface of a molecule of the crystal on the model,
coloured by d_norm, d_i or d_e, and its fingerprint plot with the shares of the contacts (crystal_hirshfeld), as in
CrystalExplorer.

§1 PURPOSE
    The roadmap, «Кристаллы: очередь дальше», 2: what Mercury itself has not — how a molecule touches its neighbours,
    all at once: the red spots of hydrogen bonds on the surface, the spikes and wings of the fingerprint, the share
    of H···H, O···H, C···H contacts.
§4 SPECIFICATION show(studio) -> HirshfeldWindow | None (the panel, nothing computed); HirshfeldWindow(parent, crystal,
    studio, centre): build_button «Построить» -> build() -> Surface | None (the molecule selected now, computed again
    only for another grid or molecule, on the model); recolour() — another colouring of the surface on the model; step
    (combo), mapped (combo: 'd_norm' | 'd_i' | 'd_e' | 'shape_index' | 'curvedness' — 0.175.0), pair (combo: None or a
    reciprocal pair 'H···O'), plot (FingerprintPlot), table (the shares of the contacts), compute() ->
    crystal_hirshfeld.Surface | None, show_on_model() -> bool, save_plot(path) -> path.
§7 TESTS tests/gui/test_gui_files.py::test_the_hirshfeld_surface_of_a_crystal.
"""

from types import SimpleNamespace

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import (QComboBox, QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel,
                               QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import crystal_hirshfeld, crystal_shell

STEPS = ((0.3, 'грубая (быстро)'), (0.2, 'средняя'), (0.12, 'точная (медленнее)'))
MAPPED = (('d_norm', 'd_norm'), ('d_i', 'd_i'), ('d_e', 'd_e'), ('shape_index', 'индекс формы'),
          ('curvedness', 'кривизна'))
LOW, HIGH, WIDTH = 0.4, 2.6, 0.01


def _ramp(t):
    """The colours of a fingerprint as CrystalExplorer: blue (little area) → green → red (much)."""
    stops = ((0.0, (40, 70, 200)), (0.35, (40, 190, 220)), (0.6, (70, 200, 80)), (0.85, (240, 210, 40)),
             (1.0, (220, 50, 40)))
    for (t0, c0), (t1, c1) in zip(stops, stops[1:]):
        if t <= t1:
            u = (t - t0) / (t1 - t0) if t1 > t0 else 0.0
            return QColor(*(int(c0[k] + (c1[k] - c0[k]) * u) for k in range(3)))
    return QColor(*stops[-1][1])


class FingerprintPlot(QWidget):
    """d_i across, d_e up, 0.4–2.6 Å; the whole plot grey under the pair chosen in colour."""

    def __init__(self):
        super().__init__()
        self.whole = None
        self.chosen = None
        self.low, self.high = LOW, HIGH  # the standard scale, or that of the data (HirshfeldWindow.bounds)
        self.setMinimumSize(320, 320)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        dark = self.palette().window().color().lightness() < 128
        p.fillRect(self.rect(), QColor('#1d2330' if dark else '#ffffff'))
        # room at the left for the numbers and the title turned along the axis, under for the other title
        left, bottom = 58, 44
        side = max(60, min(self.width() - left - 10, self.height() - 10 - bottom))
        box = QRectF(left, 10, side, side)
        ink = QColor('#c9d1dc' if dark else '#333a44')
        if self.whole is not None and self.whole.sum() > 0:
            n = self.whole.shape[0]
            cell = side / n
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor('#59606b' if dark else '#c8ccd2'))
            for i, j in np.argwhere(self.whole > 0):
                p.drawRect(QRectF(box.left() + i * cell, box.bottom() - (j + 1) * cell, cell + 0.5, cell + 0.5))
            shown = self.chosen if self.chosen is not None else self.whole
            top = float(shown.max()) or 1.0
            for i, j in np.argwhere(shown > 0):
                p.setBrush(_ramp(min(1.0, (shown[i, j] / top) ** 0.5)))
                p.drawRect(QRectF(box.left() + i * cell, box.bottom() - (j + 1) * cell, cell + 0.5, cell + 0.5))
        p.setPen(QPen(ink, 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(box)
        p.setFont(QFont(self.font().family(), 8))
        low, high = self.low, self.high
        tick = 0.1 if high - low <= 1.2 + 1e-9 else 0.2  # a label every second tick: 0.2 or 0.4 Å apart
        first = int(np.ceil(low / tick - 1e-9))
        for k in range(first, first + 40):
            value = round(k * tick, 6)
            if value > high + 1e-9:
                break
            t = (value - low) / (high - low)
            x, y = box.left() + t * side, box.bottom() - t * side
            p.drawLine(QPointF(x, box.bottom()), QPointF(x, box.bottom() + 3))
            p.drawLine(QPointF(box.left() - 3, y), QPointF(box.left(), y))
            if k % 2 == 0:
                p.drawText(QRectF(x - 14, box.bottom() + 4, 28, 12), Qt.AlignmentFlag.AlignCenter, f'{value:.1f}')
                p.drawText(QRectF(left - 40, y - 6, 34, 12), Qt.AlignmentFlag.AlignRight, f'{value:.1f}')
        title = QFont(self.font().family(), 10)
        title.setBold(True)
        p.setFont(title)
        p.drawText(QRectF(box.left(), box.bottom() + 20, side, 18), Qt.AlignmentFlag.AlignHCenter, 'dᵢ, Å')
        p.save()
        p.translate(12, box.top() + side / 2)
        p.rotate(-90)
        p.drawText(QRectF(-side / 2, -9, side, 18), Qt.AlignmentFlag.AlignHCenter, 'dₑ, Å')
        p.restore()
        p.end()


class HirshfeldWindow(QDialog):
    def __init__(self, parent, crystal, studio=None, centre=None, title=''):
        super().__init__(parent)
        self.crystal, self.studio, self.centre, self.result = crystal, studio, centre or None, None
        self.setWindowTitle(tr('Поверхность Хиршфельда · ') + (title or crystal.title or 'CIF'))
        layout = QVBoxLayout(self)
        # the panel opens with its settings — the grid, what the surface
        # is coloured by, the molecule — and «Построить» builds the surface on the model; another colouring of a
        # surface already computed is put on the model at once (the grid is not computed again)
        from PySide6.QtWidgets import QFormLayout

        from azimuth.ui import button as plain_button

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        self.step = QComboBox()
        for value, name in STEPS:
            self.step.addItem(tr(name) + f' · {value:g} Å'.replace('.', ','), value)
        self.step.setCurrentIndex(1)
        self.step.setToolTip(tr('Шаг сетки, на которой ищется поверхность: мельче — глаже и дольше'))
        form.addRow(tr('Сетка'), self.step)
        self.mapped = QComboBox()
        for key, name in MAPPED:
            self.mapped.addItem(tr(name), key)
        self.mapped.setToolTip(tr('Чем окрасить поверхность на модели: d_norm, d_i, d_e, индекс формы, кривизна'))
        self.mapped.currentIndexChanged.connect(lambda _: self.recolour())
        form.addRow(tr('Окраска'), self.mapped)
        layout.addLayout(form)
        self.where = QLabel(tr('Молекула: выделенная на модели.') if self.centre
                            else tr('Молекула: первая в ячейке (выделите атом другой молекулы на модели, чтобы взять её).'))
        self.where.setObjectName('subtitle')
        self.where.setWordWrap(True)
        layout.addWidget(self.where)
        row = QHBoxLayout()
        self.build_button = plain_button(tr('Построить'), lambda: self.build(), primary=True)
        self.build_button.setToolTip(tr('Поверхность выбранной молекулы с выбранной окраской — на модели; «отпечаток» '
                                        'и доли контактов — ниже'))
        row.addWidget(self.build_button)
        row.addStretch(1)
        self.help_slot = row
        layout.addLayout(row)
        self.summary = QLabel(tr('Выберите сетку и окраску и нажмите «Построить».'))
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        middle = QHBoxLayout()
        self.plot = FingerprintPlot()
        middle.addWidget(self.plot, 3)
        right = QVBoxLayout()
        self.pair = QComboBox()
        self.pair.setToolTip(tr('Какие контакты выделить на «отпечатке»: вместе X···Y и Y···X, как в CrystalExplorer'))
        self.pair.currentIndexChanged.connect(self.redraw)
        right.addWidget(self.pair)
        # the standard scale of CrystalExplorer (0.4–2.6 Å, the plots of all crystals comparable) or one fitted round
        # the data
        self.scale = QComboBox()
        self.scale.addItem(tr('масштаб: стандартный · 0,4–2,6 Å'), 'standard')
        self.scale.addItem(tr('масштаб: по данным'), 'data')
        self.scale.setToolTip(tr('Стандартный — как в CrystalExplorer: «отпечатки» разных кристаллов сравнимы на глаз. '
                                 'По данным — оси вокруг пятна, оно крупнее и подробнее'))
        self.scale.currentIndexChanged.connect(lambda _: self.rescale())
        right.addWidget(self.scale)
        self.table = QTableWidget(0, 2)
        self.table.setHorizontalHeaderLabels([tr('Контакт'), tr('Доля, %')])  # the long one was cut
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setMinimumSectionSize(60)
        self.table.setMinimumWidth(240)  # «Доля поверхности» was cut in the narrow panel
        right.addWidget(self.table, 1)
        middle.addLayout(right, 2)
        layout.addLayout(middle, 1)
        note = QLabel(tr('Поверхность — где сферические атомы молекулы дают половину плотности кристалла '
                         '(промолекула, атомы H на нейтронных расстояниях). d_i и d_e — расстояния от точки поверхности '
                         'до ближайшего ядра внутри и снаружи; d_norm < 0 (красное) — контакт короче суммы '
                         'ван-дер-ваальсовых радиусов. «Отпечаток» — доля площади при каждой паре (d_i, d_e). Индекс формы: '
                         'синее — выпуклость, красное — впадина, куда входит атом соседа; красные и синие треугольники '
                         '(«бабочки») — признак π–π-стопки. Кривизна: низкая — плоские участки (грани стопки).'))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        note.hide()  # the explanation is behind the «?» button
        layout.addWidget(note)
        bottom = QHBoxLayout()
        from azimuth.ui import help_button

        self.help_slot.addWidget(help_button(note.text()))
        self.model_button = action_button(tr('Показать на модели'), self.show_on_model, 'eye')
        self.model_button.hide()  # «Построить» puts it there (kept for the tests and the old calls)
        bottom.addWidget(self.model_button)
        self.save_button = action_button(tr('Сохранить «отпечаток»…'), lambda: self.save_plot(), 'save')
        self.save_button.setEnabled(False)
        bottom.addWidget(self.save_button)
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.resize(760, 620)

    def pick_centre(self):
        """The molecule of the atoms selected on the model now (the one before when nothing is selected)."""
        studio = self.studio
        viewer = getattr(studio, 'viewer', None)
        picked = list(getattr(viewer, 'selected', []) or [])
        molecule = getattr(studio, 'molecule', None)
        if picked == getattr(self, '_own_selection', None):  # the molecule of the surface, selected by its building
            return self.centre
        if picked and molecule is not None:
            atoms = molecule.atoms
            found = crystal_shell.locate(self.crystal, [(atoms[i].x, atoms[i].y, atoms[i].z) for i in picked
                                                        if i < len(atoms)])
            if found:
                self.centre = found
                self.where.setText(tr('Молекула: выделенная на модели.'))
        return self.centre

    def build(self):
        """«Построить»: the surface of the molecule chosen with the grid chosen (computed again only when they
        changed), coloured as chosen, on the model. Returns the surface or None."""
        if self.studio is not None:
            self.pick_centre()
        key = (self.step.currentData(), repr(self.centre))
        if self.result is None or getattr(self, '_key', None) != key:
            if self.compute() is None:
                return None
            self._key = key
        # the grid is computed in the background — when the user went to another
        # section (or folded the panel) meanwhile, the surface waits: the model is not taken over, the section stays
        viewer = getattr(self.studio, 'viewer', None)
        top = viewer.window() if viewer is not None else None  # the hub (or the Studio alone): what is shown in it
        if self.studio is not None and not (viewer is not None and viewer.isVisibleTo(top) and self.isVisibleTo(top)):
            notify = getattr(self.studio, 'notify', None)
            if callable(notify):
                notify(tr('Поверхность Хиршфельда посчитана — «Построить» в её панели покажет её на модели.'), 10000)
            return self.result
        if self.studio is not None:
            self.show_on_model()
            self._on_model = True
            self._own_selection = list(getattr(getattr(self.studio, 'viewer', None), 'selected', []) or [])
        return self.result

    def recolour(self):
        """Another colouring chosen: a surface already on the model takes it at once."""
        if self.result is not None and getattr(self, '_on_model', False) and self.studio is not None:
            self.show_on_model()

    def compute(self):
        # the grid is computed in a worker thread, the window paints meanwhile (the pill of the work, Esc cancels)
        from azimuth.tasks import run_waiting

        crystal, centre, step = self.crystal, self.centre, self.step.currentData()
        try:
            result = run_waiting(self, tr('Строю поверхность Хиршфельда…'),
                                 lambda _step: crystal_hirshfeld.surface(crystal, centre, step))
        except InterruptedError:
            return None
        except ValueError as exc:
            result = exc
        # the panel may have
        # been closed while the surface was computed (its button pressed again) — then nothing is shown
        try:
            from shiboken6 import isValid
        except ImportError:  # pragma: no cover
            def isValid(_):
                return True
        if not isValid(self) or not isValid(self.model_button):
            return None
        try:
            if isinstance(result, ValueError):
                raise result
            self.result = result
        except ValueError as exc:
            self.result = None
            self.summary.setText(str(exc))
            self.plot.whole = self.plot.chosen = None
            self.plot.update()
            self.table.setRowCount(0)
            self.pair.clear()
            for button in (self.model_button, self.save_button):
                button.setEnabled(False)
            return None
        r = self.result
        for button in (self.model_button, self.save_button):
            button.setEnabled(True)
        self.summary.setText(tr('Площадь {} Å², объём {} Å³, глобулярность {}; самое короткое d_norm {} ({}).').format(
            f'{r.total_area:.1f}', f'{r.volume:.1f}', f'{r.globularity:.3f}', f'{r.d_norm.min():.2f}',
            '···'.join(self._shortest(r))))
        shares = r.fractions()
        self.table.setRowCount(len(shares))
        for k, (name, share) in enumerate(shares.items()):
            self.table.setItem(k, 0, QTableWidgetItem(name))
            self.table.setItem(k, 1, QTableWidgetItem(f'{100 * share:.1f} %'))
        self.pair.blockSignals(True)
        self.pair.clear()
        self.pair.addItem(tr('все контакты'), None)
        for name in shares:
            self.pair.addItem(name, name)
        self.pair.blockSignals(False)
        self.rescale()
        return r

    def bounds(self):
        """(low, high, width) of the fingerprint: the standard square, or one round the d_i and d_e of the surface
        (to 0.1 Å, a margin of 0.05 Å) with as many bins."""
        r = self.result
        if self.scale.currentData() != 'data' or r is None or not len(r.d_i):
            return LOW, HIGH, WIDTH
        lo = float(min(r.d_i.min(), r.d_e.min())) - 0.05
        hi = float(max(r.d_i.max(), r.d_e.max())) + 0.05
        lo, hi = np.floor(lo * 10) / 10, np.ceil(hi * 10) / 10
        if hi - lo < 0.4:
            hi = lo + 0.4
        return lo, hi, WIDTH * (hi - lo) / (HIGH - LOW)

    def rescale(self):
        """The fingerprint on the scale chosen."""
        r = self.result
        low, high, width = self.bounds()
        self.plot.low, self.plot.high = low, high
        if r is None:
            self.plot.update()
            return
        self.plot.whole = r.fingerprint(low, high, width)
        self.redraw()

    @staticmethod
    def _shortest(r):
        k = int(np.argmin(r.d_norm))
        return str(r.inside[k]), str(r.outside[k])

    def redraw(self):
        r, name = self.result, self.pair.currentData()
        if r is None:
            return
        if name is None:
            self.plot.chosen = None
        else:
            a, b = name.split('···')
            low, high, width = self.bounds()
            grid = r.fingerprint(low, high, width, (a, b))
            if a != b:
                grid = grid + r.fingerprint(low, high, width, (b, a))
            self.plot.chosen = grid
        self.plot.update()

    def show_on_model(self):
        r = self.result
        if r is None or self.studio is None:
            return False
        from modules.spectrum.readers.cube import Cube

        name = self.mapped.currentData()
        tool = self.studio.crystal_tool
        molecule = tool.show_hirshfeld_model(self.crystal, r)
        if molecule is None:
            return False
        axes = np.eye(3) * r.step
        weight = Cube('Hirshfeld', molecule, r.origin, axes, r.weight[..., None], (1,), '')
        unit = '' if name in ('shape_index', 'curvedness') else 'Å'
        colour = Cube(name, molecule, r.origin, axes, crystal_hirshfeld.property_grid(r, name)[..., None], (1,), unit)
        title = tr('Поверхность Хиршфельда · ') + self.mapped.currentText()
        return bool(self.studio.surface_tool.show_surface(weight, 'hirshfeld', SimpleNamespace(molecule=molecule),
                                                          title=title, color_cube=colour, mapped=name, go=False))

    def save_plot(self, path=None):
        if self.result is None:
            return None
        if path is None:
            path, _ = QFileDialog.getSaveFileName(self, tr('Сохранить «отпечаток»'), 'fingerprint.png', 'PNG (*.png)')
            if not path:
                return None
        image = QImage(self.plot.size() * 2, QImage.Format.Format_ARGB32)
        image.setDevicePixelRatio(2)
        image.fill(Qt.GlobalColor.white)
        self.plot.render(image)
        image.save(path)
        return path


def show(studio):
    shown = getattr(studio, 'crystal', None)
    crystal = shown[0] if isinstance(shown, tuple) and shown else shown
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    # the panel of this crystal comes back as it was — its surface, its fingerprint, its settings
    kept = getattr(studio, '_hirshfeld_window', None)
    try:
        from shiboken6 import isValid
    except ImportError:  # pragma: no cover
        def isValid(_):
            return True
    tool = getattr(studio, 'crystal_tool', None)
    if kept is not None and isValid(kept):
        if kept.crystal is crystal:
            if tool is not None and hasattr(tool, 'dock'):
                tool.dock(kept)
            else:
                kept.show()
            return kept
        if not kept.isVisible():
            kept.deleteLater()
    centre = None
    viewer = getattr(studio, 'viewer', None)
    picked = list(getattr(viewer, 'selected', []) or [])
    if picked and getattr(studio, 'molecule', None) is not None:
        atoms = studio.molecule.atoms
        centre = crystal_shell.locate(crystal, [(atoms[i].x, atoms[i].y, atoms[i].z) for i in picked if i < len(atoms)])
    window = HirshfeldWindow(studio if isinstance(studio, QWidget) else None, crystal, studio, centre)
    studio._hirshfeld_window = window
    if tool is not None and hasattr(tool, 'dock'):  # beside the model, not over it
        tool.dock(window)
    else:
        window.show()
    # nothing is computed at the opening — the settings first, then «Построить»
    return window
