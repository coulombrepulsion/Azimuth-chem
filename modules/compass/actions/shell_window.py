"""«Кристалл → Молекулярная оболочка…»: a molecule of the crystal and all the molecules near it
(crystal_shell), as «Molecular Shell» of Mercury.

§1 PURPOSE
    The molecular shell, as in Mercury: the neighbours of a molecule — by a distance between atoms or by the
    contact of the van der Waals spheres — on the model, with the molecular coordination number and a table: the
    symmetry code of each neighbour, its shortest contact with the centre.
§4 SPECIFICATION
    show(studio) -> ShellWindow | None; ShellWindow(parent, crystal, studio, centre): radius (Å), mode ('distance' |
    'vdw'), compute() -> crystal_shell.Shell | None, show_on_model() -> bool. The centre: the molecules of the atoms
    selected on the model when the window opens, else the first molecule of the cell.
§7 TESTS tests/gui/test_gui_files.py::test_the_molecular_shell_of_a_crystal.
"""

from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QHBoxLayout, QHeaderView, QLabel, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import crystal_shell


class ShellWindow(QDialog):
    def __init__(self, parent, crystal, studio=None, centre=None, title=''):
        super().__init__(parent)
        self.crystal, self.studio, self.centre, self.result = crystal, studio, centre or None, None
        self.setWindowTitle(tr('Молекулярная оболочка · ') + (title or crystal.title or 'CIF'))
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.mode = QComboBox()
        self.mode.addItem(tr('Атомы ближе'), 'distance')
        self.mode.addItem(tr('Σ r(вдВ) +'), 'vdw')
        self.mode.setToolTip(tr('Соседняя молекула — та, у которой хоть один атом ближе заданного расстояния к атому '
                                'центральной, или ближе суммы ван-дер-ваальсовых радиусов плюс запас'))
        self.mode.currentIndexChanged.connect(self.mode_changed)
        row.addWidget(self.mode)
        self.radius = QDoubleSpinBox()
        self.radius.setRange(0.0, 12.0)
        self.radius.setSingleStep(0.5)
        self.radius.setDecimals(1)
        self.radius.setSuffix(' Å')
        self.radius.setValue(4.0)
        row.addWidget(self.radius)
        row.addStretch(1)
        row.addWidget(action_button(tr('Найти соседей'), self.compute, 'search'))
        layout.addLayout(row)
        self.where = QLabel(tr('Центр: молекулы выделенных атомов ({}).').format(len(self.centre)) if self.centre
                            else tr('Центр: первая молекула ячейки (выделите атом другой молекулы на модели, чтобы '
                                    'взять её).'))
        self.where.setWordWrap(True)
        self.where.setObjectName('subtitle')
        layout.addWidget(self.where)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels(['№', tr('Молекула'), tr('Код симметрии'), tr('Кратчайший контакт'), 'd, Å'])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table, 1)
        bottom = QHBoxLayout()
        self.model_button = action_button(tr('Показать на модели'), self.show_on_model, 'eye')
        bottom.addWidget(self.model_button)
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.resize(640, 460)

    def mode_changed(self):
        self.radius.setValue(4.0 if self.mode.currentData() == 'distance' else 0.5)

    def compute(self):
        try:
            self.result = crystal_shell.shell(self.crystal, self.centre, self.radius.value(),
                                              self.mode.currentData() == 'vdw')
        except ValueError as exc:
            self.summary.setText(str(exc))
            self.result = None
            self.table.setRowCount(0)
            self.model_button.setEnabled(False)
            return None
        r = self.result
        self.model_button.setEnabled(True)
        self.summary.setText(tr('Соседних молекул: {} (молекулярное координационное число); в модели {} атомов.').format(
            len(r.neighbours), len(r.molecule.atoms)) if len(r.centres) == 1 else
            tr('Соседних молекул у {} центральных: {}; в модели {} атомов.').format(
                len(r.centres), len(r.neighbours), len(r.molecule.atoms)))
        self.table.setRowCount(len(r.neighbours))
        for k, n in enumerate(r.neighbours):
            values = (str(k + 1), n.formula, n.code, f'{n.pair[0]}···{n.pair[1]}', f'{n.distance:.3f}')
            for c, text in enumerate(values):
                self.table.setItem(k, c, QTableWidgetItem(text))
        return r

    def show_on_model(self):
        if self.result is None or self.studio is None:
            return False
        return bool(self.studio.crystal_tool.build_shell(self.crystal, self.result))


def show(studio):
    shown = getattr(studio, 'crystal', None)
    crystal = shown[0] if isinstance(shown, tuple) and shown else shown
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    centre = None
    viewer = getattr(studio, 'viewer', None)
    picked = list(getattr(viewer, 'selected', []) or [])
    if picked and getattr(studio, 'molecule', None) is not None:
        atoms = studio.molecule.atoms
        centre = crystal_shell.locate(crystal, [(atoms[i].x, atoms[i].y, atoms[i].z) for i in picked if i < len(atoms)])
    window = ShellWindow(studio if isinstance(studio, QWidget) else None, crystal, studio, centre)
    studio._shell_window = window
    window.show()
    window.compute()
    return window
