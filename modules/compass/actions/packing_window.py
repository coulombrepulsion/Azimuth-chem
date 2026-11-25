"""«Кристалл → Сравнить упаковку…»: the packing of the crystal shown against another CIF or the last
optimization of the project (packing_similarity) — as «Crystal Packing Similarity» of Mercury.

§4 SPECIFICATION
    show(studio) -> PackingWindow | None; PackingWindow(parent, crystal, studio): compare_with(other, name) ->
    Similarity; open_file(path=None); with_optimization().
§7 TESTS tests/gui/test_gui_files.py::test_packing_similarity_window.
"""

from pathlib import Path

from PySide6.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)

from azimuth.i18n import tr
from azimuth.ui import action_button
from modules.compass.chemistry import packing_similarity as ps


class PackingWindow(QDialog):
    def __init__(self, parent, crystal, studio=None):
        super().__init__(parent)
        self.crystal, self.studio, self.result = crystal, studio, None
        self.setWindowTitle(tr('Сравнение упаковок · ') + (crystal.title or 'CIF'))
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        row.addWidget(action_button(tr('Сравнить с другим CIF…'), lambda: self.open_file(), 'file-open'))
        self.optimized = action_button(tr('Сравнить с последней оптимизацией проекта'), self.with_optimization, 'frames')
        self.optimized.setEnabled(self._project() is not None)
        row.addWidget(self.optimized)
        row.addStretch(1)
        layout.addLayout(row)
        self.summary = QLabel(tr('Выберите второй кристалл того же вещества.'))
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.table = QTableWidget(0, 5)
        self.table.setHorizontalHeaderLabels([tr('Молекула'), tr('От центральной, Å'), tr('Сдвиг, Å'), tr('Поворот, °'),
                                              tr('Совпала')])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        layout.addWidget(self.table, 1)
        note = QLabel(tr('Кластер — молекула и её 14 ближайших соседей по центроидам. Кластеры совмещаются по центральной '
                         'молекуле; соседняя молекула совпала, если ближайшая во втором кристалле сдвинута не больше '
                         'чем на 20 % её расстояния от центра и повёрнута не больше чем на 20° (допуски COMPACK, '
                         'Chisholm, Motherwell, 2005). Затем совпавшие молекулы совмещаются вместе: RMSD их атомов '
                         '(без H). 15 из 15 и десятые доли Å — одна упаковка; меньше — другая форма.'))
        note.setWordWrap(True)
        note.setObjectName('subtitle')
        layout.addWidget(note)
        bottom = QHBoxLayout()
        bottom.addStretch(1)
        bottom.addWidget(action_button(tr('Закрыть'), self.accept, 'close'))
        layout.addLayout(bottom)
        self.resize(640, 480)

    def _project(self):
        if self.studio is None or not hasattr(self.studio, 'research_path'):
            return None
        from azimuth import crystal_projects

        path = self.studio.research_path()
        return path if path and crystal_projects.is_crystal(path) else None

    def compare_with(self, other, name):
        try:
            self.result = ps.compare(self.crystal, other)
        except ValueError as exc:
            self.summary.setText(tr('Сравнить нельзя: {}').format(
                tr('в кристаллах разные молекулы') if 'other molecules' in str(exc) else
                tr('в кристалле нет отдельных молекул (соль или каркас)') if 'no molecules' in str(exc) else str(exc)))
            self.table.setRowCount(0)
            return None
        r = self.result
        verdict = (tr('одна упаковка') if r.matched == r.n and r.rmsd < 0.5 else
                   tr('упаковки похожи') if r.matched >= r.n * 2 // 3 else tr('упаковки разные'))
        rmsd = '—' if r.matched == 0 else f'{r.rmsd:.3f}'
        self.summary.setText(tr('С «{}»: совпало молекул {} из {}, RMSD = {} Å — {}.').format(
            name, r.matched, r.n, rmsd, verdict))
        self.table.setRowCount(len(r.rows))
        for k, (reach, shift, angle, ok) in enumerate(r.rows):
            for c, text in enumerate((str(k + 1), f'{reach:.2f}', f'{shift:.2f}', f'{angle:.1f}',
                                      tr('да') if ok else tr('нет'))):
                self.table.setItem(k, c, QTableWidgetItem(text))
        return r

    def open_file(self, path=None):
        from modules.compass.chemistry import crystal as cr

        if path is None:
            path, _ = QFileDialog.getOpenFileName(self, tr('Второй кристалл'), str(Path.home()), tr('Кристалл CIF (*.cif)'))
            if not path:
                return None
        try:
            other = cr.parse_cif(Path(path).read_text(encoding='utf-8', errors='replace'))
        except (OSError, ValueError) as exc:
            self.summary.setText(str(exc))
            return None
        return self.compare_with(other, Path(path).name)

    def with_optimization(self):
        from azimuth import crystal_projects
        from modules.compass.chemistry import crystal_steps

        project = self._project()
        if project is None:
            return None
        try:
            steps, folder = crystal_steps.project_steps(project, self.crystal, crystal_projects.title(project))
        except (OSError, ValueError, KeyError):
            steps, folder = (), None
        if not steps:
            self.summary.setText(tr('В проекте нет оптимизации с шагами.'))
            return None
        last = steps[-1]
        return self.compare_with(last.adopted or last.crystal, tr('оптимизация {}').format(Path(folder).name))


def show(studio):
    shown = getattr(studio, 'crystal', None)
    crystal = shown[0] if isinstance(shown, tuple) and shown else shown
    if crystal is None:
        studio.notify(tr('Откройте файл CIF: «Файл → Открыть…».'), 6000)
        return None
    window = PackingWindow(studio if isinstance(studio, QWidget) else None, crystal, studio)
    studio._packing_window = window
    window.show()
    return window
