"""Read-only vibrational animation; displayed time and amplitude are illustrative.

The arrows have their own length and can point both ways (filled heads,
drawn also in pictures); one period can be saved as a GIF or as XYZ frames; the geometry displaced
along the mode (+ or −, by the amplitude) can be taken to Compass — to leave a saddle point along an
imaginary mode. Frames and displacements: modules/spectrum/readers/vibration_data.py
(tests/compass/test_vibration_frames.py).
"""

from dataclasses import replace
from pathlib import Path
from modules.spectrum.views.ir_plot import IRSpectrum
from modules.spectrum.views.spectrum_extras import ExtrasMixin
from PySide6.QtWidgets import QCheckBox, QComboBox, QFileDialog
from math import pi, hypot, radians
from time import monotonic
from PySide6.QtCore import QTimer, QPointF, QSize, Qt, Signal
from PySide6.QtGui import QPainter, QPen, QColor, QPolygonF
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QSplitter,
    QLabel,
    QPushButton,
    QDoubleSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
)
from modules.compass.view.viewer import MoleculeView
from modules.compass.chemistry.builder import connections
from modules.spectrum.readers.vibration_data import normalized_vectors, displaced, vibration_frames, displaced_along, frames_xyz
from azimuth.icons import iconify
from azimuth.ui import card
from azimuth.i18n import tr
from azimuth import quill  # the messages with Quill


class ModeView(MoleculeView):
    # the field is small —
    # the molecule fills more of it than in Compass (MoleculeView.FIT 0.28)
    FIT = 0.36

    def __init__(self):
        super().__init__()
        self.empty_text = tr('Геометрия колебаний недоступна')
        self.vectors = ()
        self.show_vectors = False
        self.vector_scale = 0.3
        self.both_ways = False  # arrows to +v and to -v
        self._locked_side = 0

    def keep_camera(self):
        super().keep_camera()
        self._locked_side = min(self.width(), self.height())

    def camera(self):
        """The camera kept for the animation (keep_camera — the molecule
        does not jump while it vibrates) was kept in pixels: taken while the tab was hidden or small, it stayed small
        when the field grew. Kept here relative to the field — the molecule fills it at any size."""
        if self._paint_camera is None and self.frozen_camera is None and self.locked_camera is not None \
                and self._locked_side > 0:
            center, scale = self.locked_camera
            return center, scale * self.zoom * min(self.width(), self.height()) / self._locked_side
        return super().camera()

    def point(self, position):
        center, scale = self.camera()
        x, y, z = self.to_view(tuple(position[k] - center[k] for k in range(3)))
        return QPointF(
            self.width() / 2 + self.pan.x() + x * scale * self.depth_factor(z),
            self.height() / 2 + self.pan.y() - y * scale * self.depth_factor(z),
        )

    def paintEvent(self, event):
        super().paintEvent(event)
        if not self.show_vectors or not self.molecule:
            return
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        ink = QColor('#ffb454' if self.dark else '#b56200')
        p.setPen(QPen(ink, 2.2))
        p.setBrush(ink)
        signs = (1, -1) if self.both_ways else (1,)
        for atom, vector in zip(self.molecule.atoms, self.vectors):
            a = self.point(atom.position)
            for sign in signs:
                b = self.point(tuple(c + sign * self.vector_scale * v for c, v in zip(atom.position, vector)))
                d = b - a
                length = hypot(d.x(), d.y())
                if length < 3:
                    continue
                u = d / length
                side = QPointF(-u.y(), u.x())
                head = min(9.0, 0.45 * length)
                p.drawLine(a, b - u * head * 0.8)
                p.drawPolygon(QPolygonF([b, b - u * head + side * head * 0.5, b - u * head - side * head * 0.5]))


VIEW_CONTROLS = (  # the small buttons in the top right corner of the field of the vibration
    ('rotate-y-minus', 'Повернуть влево', lambda v: v.rotate_view('y', -radians(10))),
    ('rotate-y-plus', 'Повернуть вправо', lambda v: v.rotate_view('y', radians(10))),
    ('rotate-x-minus', 'Повернуть вверх', lambda v: v.rotate_view('x', -radians(10))),
    ('rotate-x-plus', 'Повернуть вниз', lambda v: v.rotate_view('x', radians(10))),
    ('zoom-in', 'Приблизить', lambda v: v.zoom_view(1.12)),
    ('zoom-out', 'Отдалить', lambda v: v.zoom_view(1 / 1.12)),
)


class VibrationPanel(ExtrasMixin, QWidget):
    displacedRequested = Signal(object, str)  # a geometry displaced along the mode, its description
    compassRequested = Signal(int)  # the mode chosen (its row) — on the model of Compass, page «Частоты»

    def __init__(self):
        super().__init__()
        self.modes = ()
        self.base = None
        self.current = -1
        self.phase = 0.0
        self.last_tick = 0.0
        self.timer = QTimer(self)
        self.timer.setInterval(25)
        self.timer.timeout.connect(self.tick)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        split = QSplitter()
        left = QWidget()
        col = QVBoxLayout(left)
        col.setContentsMargins(0, 0, 0, 0)
        col.setSpacing(12)
        # the spectrum, the modes and the vibration in cards with their titles, as «Энергии и частоты»
        spectrum_card, spectrum_box = card(tr('Спектр'))
        spectrum_box.setContentsMargins(14, 12, 14, 14)
        spectrum_box.setSpacing(10)
        col.addWidget(spectrum_card, 3)
        self.spectrum = IRSpectrum()
        spectrum_box.addWidget(self.spectrum, 1)
        irtools = QHBoxLayout()
        # IR or Raman (the switch is shown when the result has Raman activities)
        self.ir_kind = QComboBox()
        self.ir_kind.addItem(tr('ИК'), 'ir')
        self.ir_kind.addItem(tr('Раман: активность'), 'activity')
        self.ir_kind.addItem(tr('Раман: интенсивность (532 нм)'), 'intensity')
        self.ir_kind.addItem(tr('ВКД'), 'vcd')  # vibrational circular dichroism
        self.ir_kind.setToolTip(tr('Активность Рамана — свойство молекулы (Å⁴/а.е.м.); интенсивность — что видно в опыте '
                                   'с лазером 532 нм при 298 К: (ν₀ − ν)⁴ и заселённость уровней'))
        self.ir_kind.currentIndexChanged.connect(lambda *_: self.set_kind(self.ir_kind.currentData()))
        self.ir_kind.hide()
        self.reference_raw = None  # (modes, name) of the comparison as read; drawn as the kind chosen
        self.ir_style = QComboBox()
        self.ir_style.addItems([tr('Палочки'), tr('Гауссова кривая')])
        self.ir_style.setToolTip(tr('Способ отображения ИК-спектра'))
        # «Палоч…» — the row of the card gave the list less than its text; the number fields give way instead
        metrics = self.ir_style.fontMetrics()
        self.ir_style.setMinimumWidth(max(metrics.horizontalAdvance(self.ir_style.itemText(k))
                                          for k in range(self.ir_style.count())) + 56)
        self.ir_width = QDoubleSpinBox()
        self.ir_width.setRange(2, 200)
        from azimuth import defaults

        self.ir_width.setValue(defaults.get('ir_width'))  # «Настройки → Спектры» (was 20 cm⁻¹)
        self.ir_style.setCurrentIndex(1 if defaults.get('ir_style') == 'gauss' else 0)
        self.ir_width.setSuffix(tr(' см⁻¹'))
        self.ir_width.setToolTip(tr('Полная ширина полосы на половине высоты (FWHM)'))
        self.ir_width.setEnabled(self.ir_style.currentIndex() == 1)
        self.ir_width.setMaximumWidth(124)
        self.ir_export = QPushButton(tr('Экспорт'))
        self.ir_export.setToolTip(tr('Сохранить только график: PNG, SVG или данные CSV'))
        self.ir_compare = QPushButton(tr('Сравнить с…'))  # a second IR spectrum
        self.ir_compare.setToolTip(tr('Наложить ИК-спектр другого результата (ORCA, Gaussian, xtb, Psi4, NWChem, Q-Chem, GAMESS)'))
        self.ir_compare.clicked.connect(self.choose_reference)
        self.ir_clear = QPushButton(tr('Убрать сравнение'))
        self.ir_clear.clicked.connect(lambda: self.set_reference(None))
        self.ir_clear.hide()
        # the scaling factor of the harmonic frequencies (NIST CCCBDB for the method and basis of the result)
        self.ir_scale_on = QCheckBox(tr('Множитель'))
        self.ir_scale_on.setToolTip(tr('Умножить частоты спектра на множитель метода и базиса (гармонические частоты '
                                       'выше наблюдаемых); таблица мод остаётся как в выводе'))
        self.ir_scale = QDoubleSpinBox()
        self.ir_scale.setRange(0.80, 1.10)
        self.ir_scale.setDecimals(3)
        self.ir_scale.setSingleStep(0.001)
        self.ir_scale.setValue(1.0)
        self.ir_scale.setEnabled(False)
        self.ir_scale.setMaximumWidth(104)
        self.ir_scale_on.toggled.connect(self.update_ir)
        self.ir_scale.valueChanged.connect(self.update_ir)
        # in the card the row did not fit (the list of the view went under the width field) — the comparison
        # and the export are icons, their words in the tooltips
        iconify(self.ir_compare, 'overlay', tr('Сравнить с… · наложить ИК-спектр другого результата'))
        iconify(self.ir_export, 'download', tr('Экспорт графика: PNG, SVG или данные CSV'))
        irtools.addWidget(self.ir_kind)
        irtools.addWidget(self.ir_style)
        irtools.addWidget(self.ir_width)
        irtools.addWidget(self.ir_scale_on)
        irtools.addWidget(self.ir_scale)
        irtools.addWidget(self.ir_compare)
        irtools.addWidget(self.ir_clear)
        irtools.addWidget(self.make_extras_button(irtools))  # the experiment and the conformers
        irtools.addWidget(self.ir_export)
        spectrum_box.addLayout(irtools)
        self.ir_style.currentIndexChanged.connect(self.update_ir)
        self.ir_width.valueChanged.connect(self.update_ir)
        self.ir_export.clicked.connect(self.export_ir)

        self.table = QTableWidget(0, 7)  # + the Raman activity and the depolarization (hidden without them)
        self.table.setHorizontalHeaderLabels([tr('Мода'), tr('см⁻¹'), tr('км/моль'), tr('Векторы'), tr('Раман, Å⁴/а.е.м.'),
                                              tr('ρ'), tr('R ВКД')])  # + VCD, 10⁻⁴⁴ esu²·cm²
        self.table.horizontalHeaderItem(6).setToolTip(
            tr('Вращательная сила колебания (ВКД), 10⁻⁴⁴ esu²·см²: знак — направление полосы; у зеркального изомера '
               'знаки обратные'))
        self.table.horizontalHeaderItem(5).setToolTip(
            tr('Степень деполяризации: ρ < 0,75 — полносимметричное колебание (поляризованная полоса), '
               'ρ = 0,75 — неполносимметричное'))
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.verticalHeader().hide()
        modes_card, self.modes_box = card(tr('Моды'))
        self.modes_box.setContentsMargins(14, 12, 14, 14)
        self.modes_box.setSpacing(10)
        self.modes_box.addWidget(self.table, 1)
        col.addWidget(modes_card, 2)
        split.addWidget(left)
        right = QWidget()
        holder = QVBoxLayout(right)
        holder.setContentsMargins(0, 0, 0, 0)
        model_card, rv = card(tr('Колебание'))
        rv.setContentsMargins(14, 12, 14, 14)
        rv.setSpacing(10)
        holder.addWidget(model_card)
        self.viewer = ModeView()
        self.viewer.setMinimumSize(240, 190)
        rv.addWidget(self.view_with_controls(), 1)
        controls = QHBoxLayout()
        self.play = QPushButton()
        self.play.setCheckable(True)
        self.reset = QPushButton()
        self.arrows = QPushButton()
        self.arrows.setCheckable(True)
        self.center = QPushButton()
        iconify(self.play, 'play', tr('Воспроизвести · условная скорость'))
        iconify(self.reset, 'stop', tr('Остановить и вернуть исходную геометрию'))
        iconify(self.arrows, 'vectors', tr('Показать направления смещений'))
        iconify(self.center, 'center', tr('Центровать'))
        for b in (self.play, self.reset, self.arrows, self.center):
            controls.addWidget(b)
        controls.addStretch()
        # the same vibration on the model of Compass (the page «Частоты» of the panel on the left)
        self.compass_button = iconify(QPushButton(), 'compass', tr('Перейти в Компас · это колебание на модели'))
        self.compass_button.clicked.connect(lambda: self.compassRequested.emit(self.table.currentRow()))
        controls.addWidget(self.compass_button)
        rv.addLayout(controls)
        settings = QHBoxLayout()
        self.amplitude = QDoubleSpinBox()
        self.amplitude.setRange(0.02, 0.8)
        self.amplitude.setSingleStep(0.05)
        self.amplitude.setValue(0.25)
        self.amplitude.setSuffix(' Å')
        self.amplitude.setMaximumWidth(116)
        self.amplitude.setToolTip(
            tr(
                'Условный максимальный размах смещения одного атома от исходной позиции. Отношения смещений атомов сохранены. Это не тепловая амплитуда.'
            )
        )
        self.speed = QDoubleSpinBox()
        self.speed.setRange(0.1, 3)
        self.speed.setSingleStep(0.1)
        self.speed.setValue(0.7)
        self.speed.setSuffix(tr(' Гц'))
        self.speed.setMaximumWidth(116)
        self.speed.setToolTip(tr('Скорость показа, не физическая частота колебания. Одинакова для всех выбранных мод.'))
        self.arrow_length = QDoubleSpinBox()  # the arrows have their own length
        self.arrow_length.setRange(0.1, 3.0)
        self.arrow_length.setSingleStep(0.1)
        self.arrow_length.setValue(0.8)
        self.arrow_length.setSuffix(' Å')
        self.arrow_length.setMaximumWidth(116)
        self.arrow_length.setToolTip(tr('Длина стрелки у атома, который смещается больше всех; у остальных — пропорционально.'))
        for name, widget in [(tr('Амплитуда'), self.amplitude), (tr('Показ'), self.speed), (tr('Стрелки'), self.arrow_length)]:
            settings.addWidget(QLabel(name))
            settings.addWidget(widget)
        rv.addLayout(settings)
        more = QHBoxLayout()
        self.both = QPushButton(tr('В обе стороны'))
        self.both.setCheckable(True)
        self.both.setToolTip(tr('Стрелки к обеим крайним точкам колебания'))
        self.gif_button = QPushButton(tr('GIF…'))
        self.gif_button.setToolTip(tr('Один период колебания в GIF (кадров: 20; стрелки — если включены)'))
        self.xyz_button = QPushButton(tr('Кадры XYZ…'))
        self.xyz_button.setToolTip(tr('Один период колебания — 20 кадров в одном файле XYZ'))
        self.plus_button = QPushButton(tr('Сместить +'))
        self.minus_button = QPushButton(tr('Сместить −'))
        for button in (self.plus_button, self.minus_button):
            button.setToolTip(
                tr('Геометрия, смещённая вдоль моды на амплитуду (у самого подвижного атома), — в Компас. Для мнимой частоты — шаг от седловой точки.')
            )
        # the five buttons share the width of the row,
        # edge to edge as the row of the amplitude, the speed and the arrows over them
        for b in (self.both, self.gif_button, self.xyz_button, self.plus_button, self.minus_button):
            more.addWidget(b, 1)
        rv.addLayout(more)
        split.addWidget(right)
        split.setSizes([430, 560])
        split.setHandleWidth(12)  # the room between the cards
        layout.addWidget(split, 1)
        self.detail = QLabel(tr('Частоты ещё не загружены'))
        self.detail.setObjectName('subtitle')
        self.detail.setWordWrap(True)
        self.modes_box.addWidget(self.detail)  # under the table of the modes, in its card
        self.table.currentCellChanged.connect(lambda row, *_: self.select_mode(row))
        self.spectrum.selected.connect(lambda row: self.table.setCurrentCell(row, 0))
        self.play.toggled.connect(self.set_playing)
        self.reset.clicked.connect(self.reset_animation)
        self.center.clicked.connect(self.center_view)
        self.arrows.toggled.connect(self.toggle_arrows)
        self.amplitude.valueChanged.connect(self.draw_frame)
        self.arrow_length.valueChanged.connect(self.draw_frame)
        self.both.toggled.connect(self.toggle_both)
        self.gif_button.clicked.connect(lambda: self.save_gif())
        self.xyz_button.clicked.connect(lambda: self.save_xyz())
        self.plus_button.clicked.connect(lambda: self.request_displaced(1))
        self.minus_button.clicked.connect(lambda: self.request_displaced(-1))
        self.play.setEnabled(False)
        self.reset.setEnabled(False)
        self.arrows.setEnabled(False)
        for b in (self.both, self.gif_button, self.xyz_button, self.plus_button, self.minus_button):
            b.setEnabled(False)

    def apply_factor(self, factor):
        """A factor chosen in the handbook: into the field, the scaling switched on."""
        self.ir_scale.setValue(factor)
        self.ir_scale_on.setChecked(True)
        self.update_ir()

    def open_factor_table(self):
        """The handbook of the factors over the window, the row of the level of the result chosen; «Применить к
        спектру» (or a double click) puts the factor into the field."""
        from azimuth.handbook_window import open_handbook

        found = getattr(self, 'scale_suggestion', None)
        level = (found.method, found.basis) if found is not None else None
        return open_handbook(self.window(), 'factors', apply_factor=self.apply_factor, level=level)

    def set_level(self, level):
        """The factor of NIST CCCBDB for the level of theory of the result is put into the field (switched
        off: the spectrum stays as the program computed it until «Множитель» is ticked); none known — 1.000."""
        from modules.spectrum.analysis import scaling

        found = scaling.recommended(level) if level else None
        self.ir_scale.blockSignals(True)
        self.ir_scale.setValue(found.factor if found else 1.0)
        self.ir_scale.blockSignals(False)
        if found:
            spread = f' ± {found.uncertainty:.3f}' if found.uncertainty else ''
            self.ir_scale.setToolTip(tr('Множитель частот ') + f'{found.factor:.3f}{spread} · ' + found.note)
        else:
            self.ir_scale.setToolTip(tr('Для этого метода и базиса в NIST CCCBDB множителя нет — впишите свой'))
        self.scale_suggestion = found
        from azimuth import defaults

        if found and defaults.get('ir_scale_on') and not self.ir_scale_on.isChecked():
            self.ir_scale_on.blockSignals(True)
            self.ir_scale_on.setChecked(True)
            self.ir_scale_on.blockSignals(False)
        self.update_ir()
        return found

    def update_ir(self, *args):
        self.spectrum.smooth = self.ir_style.currentIndex() == 1
        self.spectrum.width_cm = self.ir_width.value()
        self.ir_width.setEnabled(self.spectrum.smooth)
        on = self.ir_scale_on.isChecked() if hasattr(self, 'ir_scale_on') else False
        if hasattr(self, 'ir_scale'):
            self.ir_scale.setEnabled(on)
        self.spectrum.set_scale(self.ir_scale.value() if on else 1.0)
        self.spectrum.update()

    def kinds(self):
        """The spectra the result has: IR always, Raman with activities, VCD with rotational strengths."""
        from modules.spectrum.analysis import raman

        found = ['ir']
        if raman.has_raman(self.modes):
            found += ['activity', 'intensity']
        if any(getattr(m, 'vcd', None) is not None for m in self.modes):
            found.append('vcd')
        return found

    def spectrum_modes(self, modes):
        """The modes as the plot draws them — IR as read, Raman with the activity or the intensity;
        VCD with the rotational strengths (signed)."""
        from modules.spectrum.analysis import raman

        kind = self.ir_kind.currentData() if self.ir_kind.currentData() in self.kinds() else 'ir'
        if kind == 'ir':
            return tuple(modes)
        if kind == 'vcd':
            return tuple(replace(m, intensity=getattr(m, 'vcd', None)) for m in modes)
        try:
            return raman.raman_modes(modes, kind)
        except ValueError:
            return tuple(replace(m, intensity=None) for m in modes)

    def set_kind(self, kind):
        """Draw the IR or the Raman spectrum (the factor and the comparison follow)."""
        kind = kind if kind in self.kinds() else 'ir'
        self.spectrum.kind = kind
        self.spectrum.scale, self.spectrum._original = 1.0, ()
        self.spectrum.modes = self.spectrum_modes(self.modes)
        self.spectrum._cache = None
        self._draw_reference()
        if self.ensemble_data is not None:  # the average as the kind chosen (IR, Raman or VCD)
            self.show_ensemble()
        if self.experiment_raw is not None:  # VCD is signed, IR and Raman are not
            self.show_experiment()
        self.update_ir()

    # -- the experiment and the conformers (spectrum_extras.ExtrasMixin) ----------------------------------
    EXPERIMENT_AXIS = 'cm-1'

    @property
    def plot(self):
        return self.spectrum

    def signed(self):
        return self.spectrum.signed  # VCD

    @property
    def fit_values(self):
        from modules.spectrum.analysis.experiment import FACTORS

        return FACTORS

    def fit_hint(self):
        return tr('Множитель частот 0,90–1,05, с которым расчётный спектр больше всего похож на измеренный')

    def fit_curve(self, factor):
        from modules.spectrum.analysis.experiment import scaled
        from modules.spectrum.analysis.ir_spectrum import broaden

        base = self.spectrum.ensemble[0] if self.spectrum.ensemble else self.spectrum_modes(self.modes)
        return scaled(broaden(base, self.ir_width.value(), self.spectrum.signed), factor)

    def apply_fit(self, factor):
        self.ir_scale_on.setChecked(True)
        self.ir_scale.setValue(factor)
        self.update_ir()
        from modules.spectrum.views.spectrum_extras import num

        return tr('множитель частот {}').format(num(factor, '.3f'))

    def ensemble_lists(self, outputs):
        return [self.spectrum_modes(o.modes) for o in outputs]

    def lacking_text(self):
        return tr('Нет интенсивностей этого спектра у конформеров: ')

    def set_ensemble_lines(self, lines, name):
        self.spectrum.ensemble = (tuple(lines), name) if lines else None
        self.spectrum.update()

    def _draw_reference(self):
        from modules.spectrum.analysis.ir_spectrum import lines

        reference = None
        if self.reference_raw:
            modes, name = self.reference_raw
            shown = self.spectrum_modes(modes)
            reference = (shown, name) if lines(shown, self.spectrum.signed) else None
        self.spectrum.reference = reference

    def set_reference(self, modes, name=''):
        """Draw the IR (or Raman) lines of another result too (None or no intensities: remove it)."""
        self.reference_raw = (tuple(modes), name) if modes else None
        self._draw_reference()
        self.ir_clear.setVisible(self.spectrum.reference is not None)
        self.spectrum.update()
        return self.spectrum.reference is not None

    def choose_reference(self):
        from modules.spectrum.views.spectrum_common import read_reference, reference_path, show_error

        path = reference_path(self, tr('Сравнить ИК-спектр'))
        if path:
            output = read_reference(self, path)
            if output is not None and not self.set_reference(output.modes, Path(path).name):
                show_error(self, tr('В этом файле нет ИК-интенсивностей.'))

    def export_ir(self):
        name, kind = QFileDialog.getSaveFileName(
            self, tr('Экспорт ИК-спектра'), str(Path.home() / 'Azimuth-IR.png'), 'PNG (*.png);;SVG (*.svg);;CSV (*.csv)'
        )
        if not name:
            return
        path = Path(name)
        if not path.suffix:
            path = path.with_suffix('.csv' if kind.startswith('CSV') else '.svg' if kind.startswith('SVG') else '.png')
        try:
            self.spectrum.export(path)
        except (ValueError, OSError) as exc:
            quill.warning(self, tr('Экспорт ИК-спектра'), str(exc))

    def load(self, output):
        self.reset_animation()
        self.current = -1
        self.modes = output.modes
        self.base = (
            replace(output.vibration_geometry, bonds=connections(output.vibration_geometry))
            if output.vibration_geometry
            else None
        )
        self.viewer.molecule = self.base
        self.viewer.selected = []
        self.viewer.locked_camera = None
        self.viewer.vectors = ()
        self.viewer.center_view()
        self.spectrum.scale, self.spectrum._original = 1.0, ()  # a new result (set_level applies the factor)
        from modules.spectrum.analysis import raman

        has = raman.has_raman(self.modes)
        kinds = self.kinds()  # + VCD
        for row in range(self.ir_kind.count()):
            self.ir_kind.view().setRowHidden(row, self.ir_kind.itemData(row) not in kinds)
        self.ir_kind.setVisible(len(kinds) > 1)
        for column in (4, 5):
            self.table.setColumnHidden(column, not has)
        self.table.setColumnHidden(6, 'vcd' not in kinds)
        if self.ir_kind.currentData() not in kinds:
            self.ir_kind.blockSignals(True)
            self.ir_kind.setCurrentIndex(0)
            self.ir_kind.blockSignals(False)
        self.spectrum.kind = self.ir_kind.currentData() if self.ir_kind.currentData() in kinds else 'ir'
        self.spectrum.modes = self.spectrum_modes(self.modes)
        self._draw_reference()
        self.spectrum.current = -1
        self.spectrum.update()
        self.raman_seen = raman.seen(self.modes)  # ρ of a forbidden band is 0/0 noise — not shown
        self.table.blockSignals(True)
        self.table.clearContents()
        self.table.setRowCount(len(self.modes))
        for i, m in enumerate(self.modes):
            freq = f'{abs(m.frequency):.2f}i' if m.frequency < 0 else f'{m.frequency:.2f}'
            for j, value in enumerate(
                (
                    m.index,
                    freq,
                    '—' if m.intensity is None else f'{m.intensity:.3f}',
                    tr('Есть') if m.vectors is not None else tr('Нет'),
                    '—' if m.raman_activity is None else f'{m.raman_activity:.3f}',
                    '—' if m.depolarization is None or m.index not in self.raman_seen else f'{m.depolarization:.3f}',
                    '—' if getattr(m, 'vcd', None) is None else f'{m.vcd:+.3f}',
                )
            ):
                item = QTableWidgetItem(str(value))
                self.table.setItem(i, j, item)
                if m.frequency < 0:
                    item.setForeground(QColor('#d66a35'))
                    item.setToolTip(
                        tr('Мнимая частота. Анимация показывает направление неустойчивости, а не устойчивое колебание.')
                    )
        self.table.blockSignals(False)
        row = next((i for i, m in enumerate(self.modes) if m.animatable), 0) if self.modes else -1
        if row >= 0:
            self.table.setCurrentCell(row, 0)
        self.select_mode(row)

    def select_mode(self, row):
        self.set_playing(False)
        self.current = row
        self.phase = 0.0
        self.spectrum.current = row
        self.spectrum.update()
        mode = self.modes[row] if 0 <= row < len(self.modes) else None
        enabled = bool(mode and mode.animatable and self.base)
        self.play.setEnabled(enabled)
        self.reset.setEnabled(enabled)
        self.arrows.setEnabled(enabled)
        self.amplitude.setEnabled(enabled)
        self.speed.setEnabled(enabled)
        for b in (self.arrow_length, self.both, self.gif_button, self.xyz_button, self.plus_button, self.minus_button):
            b.setEnabled(enabled)
        self.center.setEnabled(self.base is not None)
        self.viewer.vectors = normalized_vectors(mode) if enabled else ()
        if mode:
            freq = f'{abs(mode.frequency):.2f}i' if mode.frequency < 0 else f'{mode.frequency:.2f}'
            detail = tr(f'Мода {mode.index} · {freq} см⁻¹')
            if mode.frequency < 0:
                detail += tr(' · Мнимая частота: показ направления неустойчивости')
            if mode.raman_activity is not None and mode.index not in getattr(self, 'raman_seen', ()):
                detail += tr(' · в Рамане не видно (активность ≈ 0)')
            elif mode.raman_activity is not None and mode.depolarization is not None:
                band = (tr('деполяризованная полоса: колебание неполносимметричное')
                        if mode.depolarization > 0.75 - 0.005 else tr('поляризованная полоса: колебание полносимметричное'))
                detail += tr(f' · Раман {mode.raman_activity:.2f} Å⁴/а.е.м., ρ = {mode.depolarization:.3f} — ') + band
            if not enabled:
                detail += ' · ' + (
                    tr('Нулевая мода') if mode.frequency == 0 else tr('Нет полных смещений или согласованной геометрии')
                )
            self.detail.setText(detail)
        else:
            self.detail.setText(tr('Частоты не найдены. Откройте результат расчёта частот ORCA.'))
        self.draw_frame()

    def set_playing(self, playing):
        playing = bool(playing and self.play.isEnabled())
        self.play.blockSignals(True)
        self.play.setChecked(playing)
        self.play.blockSignals(False)
        iconify(
            self.play,
            'pause' if playing else 'play',
            tr('Пауза') if playing else tr('Воспроизвести · условная скорость'),
        )
        if playing:
            if self.viewer.locked_camera is None:
                self.viewer.keep_camera()
            self.last_tick = monotonic()
            self.timer.start()
        else:
            self.timer.stop()

    def reset_animation(self):
        self.set_playing(False)
        self.phase = 0.0
        self.draw_frame()

    def tick(self):
        now = monotonic()
        self.phase = (self.phase + 2 * pi * self.speed.value() * min(0.1, now - self.last_tick)) % (2 * pi)
        self.last_tick = now
        self.viewer.moving()  # animation frames are fast frames; a still frame is drawn in full quality
        self.draw_frame()

    def draw_frame(self, *args):
        if self.base:
            if self.viewer.locked_camera is None:
                self.viewer.set_molecule(self.base)
                self.viewer.keep_camera()
            self.viewer.set_molecule(
                displaced(self.base, self.viewer.vectors, self.amplitude.value(), self.phase)
                if self.viewer.vectors
                else self.base
            )
        else:
            self.viewer.molecule = None
        self.viewer.vector_scale = self.arrow_length.value()
        self.viewer.update()

    def center_view(self):
        if self.base:
            self.viewer.set_molecule(self.base)
        self.viewer.center_view()
        self.viewer.keep_camera()
        self.draw_frame()

    def toggle_arrows(self, on):
        self.viewer.show_vectors = on
        self.viewer.update()

    def toggle_both(self, on):
        self.viewer.both_ways = bool(on)
        self.viewer.update()

    # -- frames, files and displaced geometries ------------------------------------------
    def mode_label(self):
        mode = self.modes[self.current]
        freq = f'{abs(mode.frequency):.2f}i' if mode.frequency < 0 else f'{mode.frequency:.2f}'
        return tr(f'мода {mode.index}, {freq} см⁻¹')

    def frames(self, count=20):
        if not self.viewer.vectors or self.base is None:
            raise ValueError(tr('Выберите колебание с векторами смещений.'))
        return vibration_frames(self.base, self.viewer.vectors, self.amplitude.value(), count)

    def save_gif(self, path=None, count=20):
        """One period as an animated GIF of the field (arrows included when shown); returns the path."""
        from modules.compass.view.gif import write_gif
        from azimuth.ui import ask_picture_path

        try:
            frames = self.frames(count)
        except ValueError as exc:
            quill.warning(self, tr('GIF колебания'), str(exc))
            return None
        if path is None:
            path = ask_picture_path(self, tr('Сохранить GIF'), f'Azimuth-mode-{self.modes[self.current].index}', '.gif')
            if path is None:
                return None
        playing = self.play.isChecked()
        self.set_playing(False)
        if self.viewer.locked_camera is None:
            self.viewer.set_molecule(self.base)
            self.viewer.keep_camera()
        images = []
        try:
            for frame in frames:
                self.viewer.set_molecule(frame)
                images.append(self.viewer.render_image(1, False).toImage())
            delay = max(20, round(1000 / (self.speed.value() * count)))  # one period at the display speed
            write_gif(path, images, delay)
        except (OSError, ValueError) as exc:
            quill.warning(self, tr('GIF колебания'), str(exc))
            return None
        finally:
            self.draw_frame()
            self.set_playing(playing)
        return path

    def save_xyz(self, path=None, count=20):
        try:
            text = frames_xyz(self.frames(count), self.mode_label())
        except ValueError as exc:
            quill.warning(self, tr('Кадры колебания'), str(exc))
            return None
        if path is None:
            name, _ = QFileDialog.getSaveFileName(
                self, tr('Сохранить кадры колебания'), str(Path.home() / f'mode-{self.modes[self.current].index}.xyz'), 'XYZ (*.xyz)'
            )
            if not name:
                return None
            path = name
        from azimuth.files import atomic_write

        atomic_write(path, text)
        return path

    def request_displaced(self, sign):
        if not self.viewer.vectors or self.base is None:
            return None
        molecule = displaced_along(self.base, self.viewer.vectors, self.amplitude.value(), sign)
        text = self.mode_label() + (' · +' if sign > 0 else ' · −') + f'{self.amplitude.value():.2f} Å'
        self.displacedRequested.emit(molecule, text)
        return molecule

    def ensure_selection_visible(self):
        try:
            item = self.table.item(self.current, 0)
        except RuntimeError:  # the panel was deleted before the timer fired
            return
        if item:
            self.table.scrollToItem(item)

    def view_with_controls(self):
        """The field and, over its top right corner, small buttons — turns of 10°
        about the axes of the screen and the zoom; held, they repeat. Siblings of the field in one cell of a grid (not
        its children: the field may draw with VTK in a child of its own)."""
        holder = QWidget()
        grid = QGridLayout(holder)
        grid.setContentsMargins(0, 0, 0, 0)
        grid.addWidget(self.viewer, 0, 0)
        bar = QWidget()
        row = QHBoxLayout(bar)
        row.setContentsMargins(0, 6, 6, 0)
        row.setSpacing(2)
        self.view_controls = []
        for name, title, act in VIEW_CONTROLS:
            item = iconify(QPushButton(), name, tr(title) + tr(' · можно удерживать'))
            item.setFixedSize(26, 26)
            item.setIconSize(QSize(16, 16))
            item.setAutoRepeat(True)
            item.setAutoRepeatDelay(350)
            item.setAutoRepeatInterval(60)
            item.clicked.connect(lambda checked=False, a=act: a(self.viewer))
            row.addWidget(item)
            self.view_controls.append(item)
        grid.addWidget(bar, 0, 0, Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignRight)
        bar.raise_()
        return holder

    def resizeEvent(self, event):
        super().resizeEvent(event)
        QTimer.singleShot(0, self, self.ensure_selection_visible)  # dies with the panel

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(0, self, self.ensure_selection_visible)

    def hideEvent(self, event):
        self.set_playing(False)
        super().hideEvent(event)
