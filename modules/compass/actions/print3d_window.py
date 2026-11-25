"""«Файл → Модель для 3D-печати…»: the model on the screen as STL or VRML for a 3D printer (print3d).

§1 PURPOSE
    The roadmap, «Кристаллы: очередь дальше», 6 (Mercury's «Print 3D»): a molecule, a block of cells or a molecular
    shell — what Compass shows — printed as balls and sticks for a lesson.
§4 SPECIFICATION
    show(studio) -> Print3DWindow | None; Print3DWindow(parent, studio): scale (mm per Å), thickness (the thinnest
    rod, mm), colored (the bonds in the colours of their atoms, for VRML), cell (the edges of the cell, when the
    crystal shows them), size (a label: the size of the model in mm); model() -> [print3d.Part]; save(kind, path=None)
    -> path | None, kind 'stl' or 'vrml'.
§7 TESTS tests/gui/test_gui_files.py::test_a_model_for_3d_printing.
"""

from PySide6.QtWidgets import QCheckBox, QDialog, QDoubleSpinBox, QFileDialog, QFormLayout, QHBoxLayout, QLabel, QVBoxLayout

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import print3d


class Print3DWindow(QDialog):
    def __init__(self, parent, studio):
        super().__init__(parent)
        self.studio = studio
        self.setWindowTitle(tr('Модель для 3D-печати'))
        layout = QVBoxLayout(self)
        note = QLabel(tr('Шарики и палочки модели на экране — молекула, блок ячеек или оболочка — для 3D-принтера. '
                         'STL — одним цветом (подходит любому принтеру), VRML — в цветах элементов. Размеры в '
                         'миллиметрах; связи не тоньше заданной толщины, иначе ломаются при печати.'))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        layout.addWidget(note)
        form = QFormLayout()
        self.scale = QDoubleSpinBox()
        self.scale.setRange(2.0, 50.0)
        self.scale.setDecimals(1)
        self.scale.setValue(print3d.SCALE)
        self.scale.setSuffix(tr(' мм на Å'))
        form.addRow(tr('Масштаб'), self.scale)
        self.thickness = QDoubleSpinBox()
        self.thickness.setRange(0.8, 6.0)
        self.thickness.setDecimals(1)
        self.thickness.setSingleStep(0.2)
        self.thickness.setValue(print3d.MIN_ROD)
        self.thickness.setSuffix(tr(' мм'))
        form.addRow(tr('Связи не тоньше'), self.thickness)
        self.colored = QCheckBox(tr('Связи в цветах своих атомов (VRML)'))
        self.colored.setChecked(True)
        form.addRow(self.colored)
        self.cell = QCheckBox(tr('Рёбра ячейки'))
        lines = getattr(getattr(studio, 'viewer', None), 'cell_lines', None)
        self.cell.setEnabled(bool(lines))
        self.cell.setChecked(bool(lines))
        form.addRow(self.cell)
        layout.addLayout(form)
        self.size = QLabel()
        layout.addWidget(self.size)
        buttons = QHBoxLayout()
        buttons.addWidget(action_button(tr('Сохранить STL…'), lambda: self.save('stl'), 'save'))
        buttons.addWidget(action_button(tr('Сохранить VRML…'), lambda: self.save('vrml'), 'save'))
        buttons.addStretch(1)
        buttons.addWidget(action_button(tr('Закрыть'), self.reject, 'close'))
        layout.addLayout(buttons)
        for widget in (self.scale, self.thickness):
            widget.valueChanged.connect(self.update_size)
        self.cell.toggled.connect(self.update_size)
        self.update_size()

    def model(self, colored=False):
        viewer = getattr(self.studio, 'viewer', None)
        molecule = getattr(self.studio, 'molecule', None)
        colors = dict(getattr(viewer, 'palette', None) or {}) if colored else None
        hidden = viewer.hidden_atoms() if viewer is not None and hasattr(viewer, 'hidden_atoms') else ()
        bonds = viewer.drawn_bonds() if viewer is not None and hasattr(viewer, 'drawn_bonds') else None
        edges = (getattr(viewer, 'cell_lines', None) or ()) if self.cell.isChecked() else ()
        return print3d.parts(molecule, scale=self.scale.value(), min_rod=self.thickness.value(), bonds=bonds,
                             edges=edges, colors=colors, hidden=hidden)

    def update_size(self):
        try:
            dx, dy, dz = print3d.size(self.model())
        except ValueError as exc:
            self.size.setText(str(exc))
            return None
        self.size.setText(tr('Размер модели: {} × {} × {} мм').format(f'{dx:.0f}', f'{dy:.0f}', f'{dz:.0f}'))
        return dx, dy, dz

    def save(self, kind, path=None):
        try:
            model = self.model(colored=kind == 'vrml' and self.colored.isChecked())
        except ValueError as exc:
            self.studio.error(exc)
            return None
        molecule = getattr(self.studio, 'molecule', None)
        name = ''.join(ch if ch.isalnum() else '_' for ch in (getattr(molecule, 'title', '') or 'model')) or 'model'
        extension = '.stl' if kind == 'stl' else '.wrl'
        if path is None:
            from pathlib import Path

            kinds = tr('STL для 3D-печати (*.stl)') if kind == 'stl' else tr('VRML 2.0 (*.wrl *.vrml)')
            path, _ = QFileDialog.getSaveFileName(self, tr('Модель для 3D-печати'), str(Path.home() / (name + extension)),
                                                  kinds)
            if not path:
                return None
        try:
            (print3d.write_stl if kind == 'stl' else print3d.write_vrml)(model, path)
        except OSError as exc:
            self.studio.error(exc)
            return None
        if hasattr(self.studio, 'notify'):
            self.studio.notify(tr('Сохранено: ') + str(path), 8000)
        return path


def show(studio):
    if not getattr(getattr(studio, 'molecule', None), 'atoms', None):
        studio.notify(tr('Нет атомов — печатать нечего.'), 6000)
        return None
    from PySide6.QtWidgets import QWidget

    window = Print3DWindow(studio if isinstance(studio, QWidget) else None, studio)
    studio._print3d_window = window
    window.show()
    return window
