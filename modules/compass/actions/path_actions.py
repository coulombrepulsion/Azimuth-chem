"""Compass: «Путь между структурами…» — images between the structure and another one, the NEB task.

§1 THEORY modules/compass/chemistry/reaction_path.py §1.
§2 ALGORITHM The start is the structure in Compass, the end a file (any format Compass reads) or the
               structure laid over it for comparison. The end is renumbered after the start and turned onto
               it (overlay.superimpose; RMSD shown). «Построить» puts the start, the images (IDPP or linear)
               and the end into the steps drawer (they can be played, saved as GIF); «Сохранить кадры XYZ…»
               writes them as one multi-frame file; «В Секстант: ORCA NEB-CI» keeps the aligned end and the
               number of images for Sextant, chooses ORCA and the task «Путь реакции (NEB-CI)» and opens
               Sextant (the input then holds %neb with end.xyz).
§3 APPLICATIONS «Правка → Путь между структурами…».
§4 SPECIFICATION PathWindow(owner): set_end(structure, name) -> bool, build() -> frames | None,
               save_xyz(path=None), to_sextant(); compass_dialogs.path() (actions/dialog_openers.py).
§5 PROCEDURES below.
§6 NOTES the images are a guess for NEB, not a path of the energy: their energies are unknown until a
               calculation.
§7 TESTS tests/test_gui.py::test_reaction_path_window_and_neb_input.
§8' ROBUSTNESS a different composition, a damaged file: a message, nothing changes.
"""

from types import SimpleNamespace

from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)

from modules.compass.chemistry import reaction_path as rp
from azimuth.i18n import set_combo_key, tr
from azimuth.ui import action_button


class PathWindow(QDialog):
    def __init__(self, owner):
        super().__init__(owner)
        self.owner = owner
        self.setWindowTitle(tr('Путь между структурами'))
        self.start = owner.coordinate_tool.table_molecule()
        self.end = None
        self.end_name = ''
        self.frames = None
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(tr(f'Начало — структура в Компасе: {self.start.formula}, атомов {len(self.start.atoms)}.')))
        self.end_label = QLabel(tr('Конец не выбран.'))
        self.end_label.setWordWrap(True)
        layout.addWidget(self.end_label)
        row = QHBoxLayout()
        pick = action_button(tr('Открыть конечную структуру…'), self.choose_end, 'file-open')
        row.addWidget(pick)
        take = QPushButton(tr('Взять из сравнения'))
        take.setToolTip(tr('Структура, наложенная для сравнения («Сравнить» над моделью)'))
        take.setEnabled(getattr(owner, 'compare_structure', None) is not None)
        take.clicked.connect(lambda: self.set_end(owner.compare_structure, owner.compare_name))
        row.addWidget(take)
        layout.addLayout(row)
        grid = QGridLayout()
        self.images = QSpinBox()
        self.images.setRange(1, 50)
        self.images.setValue(8)
        grid.addWidget(QLabel(tr('Промежуточных структур')), 0, 0)
        grid.addWidget(self.images, 0, 1)
        self.method = QComboBox()
        self.method.addItem(tr('IDPP (расстояния — плавно)'), 'idpp')
        self.method.addItem(tr('Линейная (координаты)'), 'linear')
        self.method.setToolTip(tr('IDPP интерполирует межатомные расстояния: при вращении группы связи не укорачиваются'))
        grid.addWidget(QLabel(tr('Способ')), 1, 0)
        grid.addWidget(self.method, 1, 1)
        layout.addLayout(grid)
        self.status = QLabel('')
        self.status.setWordWrap(True)
        layout.addWidget(self.status)
        buttons = QHBoxLayout()
        self.build_button = QPushButton(tr('Построить'))
        self.build_button.setDefault(True)
        self.build_button.clicked.connect(self.build)
        self.save_button = action_button(tr('Сохранить кадры XYZ…'), lambda: self.save_xyz(), 'save')
        self.neb_button = QPushButton(tr('В Секстант: ORCA NEB-CI'))
        self.neb_button.setToolTip(tr('Входной файл ORCA для поиска пути реакции и переходного состояния (NEB с climbing image)'))
        self.neb_button.clicked.connect(self.to_sextant)
        close = action_button(tr('Закрыть'), self.reject, 'close')
        for item in (self.build_button, self.save_button, self.neb_button):
            item.setEnabled(False)
            buttons.addWidget(item)
        buttons.addStretch(1)
        buttons.addWidget(close)
        layout.addLayout(buttons)

    def choose_end(self):
        from PySide6.QtWidgets import QFileDialog
        from pathlib import Path

        path, _ = QFileDialog.getOpenFileName(self, tr('Конечная структура'), str(Path.home()), tr(self.owner.OPEN_FILTER))
        if not path:
            return False
        from modules.compass.actions.overlay_actions import structure_from_path

        try:
            structure = structure_from_path(path)
        except (OSError, ValueError) as exc:
            self.owner.error(exc)
            return False
        if isinstance(structure, tuple):
            structure = structure[0]
        return self.set_end(structure, Path(path).name)

    def set_end(self, structure, name):
        try:
            _, end, rmsd = rp.ends(self.start, structure)
        except ValueError as exc:
            self.owner.error(exc)
            return False
        self.end, self.end_name = end, name
        self.end_label.setText(tr(f'Конец — {name}: атомы перенумерованы как в начале и наложены, RMSD {rmsd:.3f} Å.'))
        self.build_button.setEnabled(True)
        self.frames = None
        self.save_button.setEnabled(False)
        self.neb_button.setEnabled(True)
        return True

    def build(self):
        if self.end is None:
            return None
        try:
            frames, _ = rp.path(self.start, self.end, self.images.value(), self.method.currentData(), renumber=False)
        except ValueError as exc:
            self.owner.error(exc)
            return None
        from modules.spectrum.readers.results import OptimizationStep

        self.frames = frames
        steps = tuple(OptimizationStep(k, None, f) for k, f in enumerate(frames))
        owner = self.owner
        owner.trajectory_tool.load_trajectory(SimpleNamespace(steps=steps, scan=None, initial_geometry=None), tr('путь между структурами'))
        owner.opening_tool.show_trajectory_drawer()
        self.save_button.setEnabled(True)
        self.status.setText(tr(f'Кадров: {len(frames)} — в панели шагов (☰); их можно проиграть и записать в GIF.'))
        return frames

    def save_xyz(self, path=None):
        if not self.frames:
            return None
        text = rp.frames_xyz(self.frames, f'Azimuth path {self.start.formula}')
        if path is None:
            return self.owner.save_text(tr('Сохранить кадры пути'), 'XYZ (*.xyz)', text, 'path.xyz') or None
        from azimuth.files import atomic_write

        atomic_write(path, text)
        return path

    def to_sextant(self):
        if self.end is None:
            return False
        owner = self.owner
        from dataclasses import replace

        from azimuth.core import NEB_TASK

        owner.neb_end = replace(self.end, title=self.end_name or tr('конец пути'))
        owner.neb_images = self.images.value()
        if hasattr(owner, 'program'):
            owner.program.setCurrentIndex(max(0, owner.program.findData('orca')))
            set_combo_key(owner.task, NEB_TASK)
            owner.navigate(1)
            owner.input_tool.refresh_input()
        self.accept()
        return True
