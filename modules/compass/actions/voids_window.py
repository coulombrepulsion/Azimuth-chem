"""«Кристалл → Пустоты…»: the voids of the crystal shown (crystal_voids) — their volume, the separate
cavities and channels, the surface on the model.

§1 PURPOSE
    Voids, as «Display Voids» of Mercury: where a
    solvent molecule (a probe sphere) fits between the molecules; the voids of a solvate, the channels of a zeolite or a
    metal–organic framework.
§4 SPECIFICATION
    show(studio) -> VoidsWindow | None; VoidsWindow(parent, crystal, studio): probe (Å), step (Å), compute() -> Voids,
    show_on_model() -> bool.
§7 TESTS tests/gui/test_gui_files.py::test_the_voids_of_a_crystal.
"""

from types import SimpleNamespace

from PySide6.QtWidgets import (QComboBox, QDialog, QDoubleSpinBox, QHBoxLayout, QHeaderView, QLabel, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import crystal_voids

STEPS = ((0.3, 'грубая (быстро)'), (0.2, 'средняя'), (0.12, 'точная (медленнее)'))


class VoidsWindow(QDialog):
    def __init__(self, parent, crystal, studio=None, title=''):
        super().__init__(parent)
        self.crystal, self.studio, self.result = crystal, studio, None
        self.setWindowTitle(tr('Пустоты · ') + (title or crystal.title or 'CIF'))
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(QLabel(tr('Радиус пробы:')))
        self.probe = QDoubleSpinBox()
        self.probe.setRange(0.2, 3.0)
        self.probe.setSingleStep(0.1)
        self.probe.setDecimals(1)
        self.probe.setSuffix(' Å')
        self.probe.setValue(1.2)
        self.probe.setToolTip(tr('1,2 Å — как в Mercury; 1,4 Å — молекула воды; меньше — любые щели'))
        row.addWidget(self.probe)
        row.addWidget(QLabel(tr('Сетка:')))
        self.step = QComboBox()
        for value, name in STEPS:
            self.step.addItem(tr(name) + f' · {value:g} Å'.replace('.', ','), value)
        self.step.setCurrentIndex(1)
        row.addWidget(self.step)
        row.addStretch(1)
        row.addWidget(action_button(tr('Посчитать пустоты'), self.compute, 'voids'))
        layout.addLayout(row)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels([tr('Пустота'), tr('Объём, Å³'), tr('Доля ячейки'), tr('Вид')])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        note = QLabel(tr('Пустота — место, куда помещается пробная сфера, не задевая ван-дер-ваальсовых сфер атомов '
                         '(радиусы Бонди); на модели — объединение всех таких сфер («контактная поверхность» Mercury). '
                         'Канал проходит через всю ячейку и продолжается в соседней; полость замкнута. Атомы водорода '
                         'рентгеноструктурных файлов могут отсутствовать — тогда пустоты больше настоящих.'))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        layout.addWidget(note)
        bottom = QHBoxLayout()
        self.model_button = action_button(tr('Показать на модели'), self.show_on_model, 'eye')
        bottom.addWidget(self.model_button)
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.resize(640, 440)

    def compute(self):
        try:
            self.result = crystal_voids.voids(self.crystal, self.probe.value(), self.step.currentData())
        except ValueError as exc:
            self.summary.setText(str(exc))
            self.result = None
            return None
        r = self.result
        self.model_button.setEnabled(r.volume > 0)
        if not r.parts:
            self.summary.setText(tr('Пустот для пробы {} Å нет: молекулы упакованы плотнее.').format(
                f'{r.probe:g}'.replace('.', ',')))
        else:
            self.summary.setText(tr('Пустоты: {} Å³ на ячейку ({} Å³) — {} % объёма; отдельных пустот в ячейке: {}.').format(
                f'{r.volume:.1f}', f'{r.cell_volume:.1f}', f'{100 * r.fraction:.1f}', len(r.parts)))
        self.table.setRowCount(len(r.parts))
        for k, (volume, axes) in enumerate(r.parts):
            kind = tr('канал вдоль {}').format(', '.join(axes)) if axes else tr('полость')
            for c, text in enumerate((str(k + 1), f'{volume:.1f}', f'{100 * volume / r.cell_volume:.1f} %', kind)):
                self.table.setItem(k, c, QTableWidgetItem(text))
        return r

    def show_on_model(self):
        if self.result is None or self.studio is None or not self.result.volume:
            return False
        import numpy as np

        from modules.compass.chemistry import crystal_field

        molecule = self.studio.molecule
        rows = np.array(self.crystal.cell.vectors(), dtype=float)
        title = tr('Пустоты кристалла · проба {} Å').format(f'{self.result.probe:g}'.replace('.', ','))
        cube = crystal_field.model_cube(self.result.field, rows, molecule, title, '')
        return bool(self.studio.surface_tool.show_surface(cube, 'void', SimpleNamespace(molecule=molecule), title=title))


def show(studio):
    shown = getattr(studio, 'crystal', None)
    crystal = shown[0] if isinstance(shown, tuple) and shown else shown
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    window = VoidsWindow(studio if isinstance(studio, QWidget) else None, crystal, studio)
    studio._voids_window = window
    window.show()
    window.compute()
    return window
