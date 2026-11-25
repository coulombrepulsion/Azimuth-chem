"""«Кристалл → Плоскости (hkl) в ячейке…»: the lattice planes of a reflection drawn in the block shown
(lattice_planes), their spacing and the line of the powder pattern — as the hkl planes of Mercury.

§4 SPECIFICATION
    show(studio) -> PlanesWindow | None; PlanesWindow(parent, crystal, studio): hkl() -> (h, k, l); update_info() ->
    text; show_planes() / clear().
§7 TESTS tests/gui/test_gui_files.py::test_lattice_planes_in_the_cell.
"""

from math import asin, degrees

from PySide6.QtWidgets import QDialog, QHBoxLayout, QLabel, QSpinBox, QVBoxLayout, QWidget

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import lattice_planes, powder


class PlanesWindow(QDialog):
    def __init__(self, parent, crystal, studio=None, hkl=(1, 0, 0)):
        super().__init__(parent)
        self.crystal, self.studio = crystal, studio
        self.setWindowTitle(tr('Плоскости (hkl) · ') + (crystal.title or 'CIF'))
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Индексы Миллера:')))
        self.boxes = []
        for name, value in zip('hkl', hkl):
            box = QSpinBox()
            box.setRange(-6, 6)
            box.setValue(value)
            box.setPrefix(name + ' = ')
            box.valueChanged.connect(lambda _: self.update_info())
            self.boxes.append(box)
            row.addWidget(box)
        row.addStretch(1)
        layout.addLayout(row)
        self.info = QLabel()
        self.info.setWordWrap(True)
        layout.addWidget(self.info)
        try:
            self.lines = powder.pattern(crystal, powder.CU, 2.0, 170.0)
        except ValueError:
            self.lines = ()
        note = QLabel(tr('Плоскости h x + k y + l z = m (x, y, z — доли ячейки, m — целые) делят ячейку на |h|, |k|, |l| '
                         'частей вдоль a, b, c; расстояние между соседними — d отражения hkl в законе Брэгга '
                         'λ = 2d sin θ. Двойной щелчок по линии дифрактограммы показывает её плоскости здесь же.'))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        layout.addWidget(note)
        bottom = QHBoxLayout()
        bottom.addWidget(action_button(tr('Показать на модели'), self.show_planes, 'eye'))
        bottom.addWidget(action_button(tr('Убрать плоскости'), self.clear, 'remove'))
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.update_info()
        self.resize(560, 220)

    def hkl(self):
        return tuple(box.value() for box in self.boxes)

    def update_info(self):
        hkl = self.hkl()
        if not any(hkl):
            self.info.setText(tr('Индексы Миллера (0 0 0) не задают плоскость.'))
            return self.info.text()
        d = lattice_planes.spacing(self.crystal.cell, hkl)
        text = tr('d = {} Å').format(f'{d:.4f}')
        q = powder.CU / (2 * d)
        if q < 1:
            text += ' · ' + tr('2θ (Cu Kα₁) = {}°').format(f'{2 * degrees(asin(q)):.3f}')
        line = next((x for x in self.lines if abs(x.d - d) < 1e-5), None)
        if line is not None:
            text += ' · ' + tr('линия дифрактограммы {}, I = {} %').format(
                ' '.join(str(x) for x in line.hkl), f'{line.intensity:.1f}')
        elif q < 1:
            text += ' · ' + tr('отражения нет: погасание группы или атомы гасят его (F = 0)')
        self.info.setText(text)
        return text

    def show_planes(self):
        if self.studio is None:
            return None
        return self.studio.crystal_tool.show_lattice_planes(self.hkl())

    def clear(self):
        if self.studio is not None:
            self.studio.crystal_tool.show_lattice_planes(None)


def show(studio):
    shown = getattr(studio, 'crystal', None)
    crystal = shown[0] if isinstance(shown, tuple) and shown else shown
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    window = PlanesWindow(studio if isinstance(studio, QWidget) else None, crystal, studio)
    studio._planes_window = window
    window.show()
    window.show_planes()
    return window
