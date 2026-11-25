"""The tab «Делокализация и ароматичность» of Spectrum: the rings with HOMA (from the geometry, at once) and
FLU, PDI, MCI; the delocalization indices of the atom pairs and the localization indices of the atoms (Multiwfn,
fuzzy atomic spaces; modules/spectrum/analysis/delocalization.py).

§4 SPECIFICATION
    DelocalizationPanel(): set_source(geometry, multiwfn) — geometry() -> Molecule | None, multiwfn() -> (program,
    file, cores) | None; show_result() (after a result: the rings and their HOMA); compute_di() -> bool;
    compute_rings() -> bool; rings (list), lidi (dict | None), ring_values (dict | None); tables ring_table,
    pair_table, atom_table. FLOOR — the smallest DI listed.
§7 TESTS tests/test_gui.py::test_delocalization_and_aromaticity_tab.
"""

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from azimuth.i18n import tr
from azimuth.ui import card
from modules.spectrum.analysis import delocalization

FLOOR = 0.05  # DI below this (pairs far apart) is not listed


def _table(headers):
    table = QTableWidget(0, len(headers))
    table.setHorizontalHeaderLabels([tr(h) for h in headers])
    table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    table.verticalHeader().hide()
    table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
    table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
    return table


def _fill(table, rows):
    table.setRowCount(len(rows))
    for i, row in enumerate(rows):
        for j, value in enumerate(row):
            item = QTableWidgetItem(value)
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            table.setItem(i, j, item)


class DelocalizationPanel(QWidget):
    def __init__(self):
        super().__init__()
        self.geometry = self.multiwfn = None
        self.molecule = None
        self.rings = []
        self.lidi = self.ring_values = None
        column = QVBoxLayout(self)
        column.setSpacing(12)
        ring_card, rings = card(tr('Ароматичность циклов'))
        rings.setContentsMargins(14, 12, 14, 14)
        self.ring_note = QLabel(tr('HOMA — по длинам связей (1 у бензола, 0 у структуры Кекуле); FLU (0 у бензола), PDI '
                                   'и MCI (чем больше, тем ароматичнее) — по индексам делокализации, Multiwfn, только '
                                   'закрытая оболочка.'))
        self.ring_note.setObjectName('subtitle')
        self.ring_note.setWordWrap(True)
        rings.addWidget(self.ring_note)
        self.ring_table = _table(('Цикл', 'HOMA', 'FLU', 'PDI', 'MCI', 'MCI норм.'))
        rings.addWidget(self.ring_table, 1)
        row = QHBoxLayout()
        self.rings_button = QPushButton(tr('Посчитать FLU, PDI, MCI'))
        self.rings_button.clicked.connect(self.compute_rings)
        row.addWidget(self.rings_button)
        row.addStretch(1)
        rings.addLayout(row)
        column.addWidget(ring_card, 2)
        di_card, di = card(tr('Индексы делокализации'))
        di.setContentsMargins(14, 12, 14, 14)
        self.di_note = QLabel(tr('Сколько электронных пар делят два атома (нечёткие атомы Беке): около 1 у одинарной связи, '
                                 '1,4–1,5 у ароматической, около 2 у двойной, сотые — у водородной; у металла — ковалентная '
                                 'связь или ионная. Локализация — сколько электронов остаётся на атоме.'))
        self.di_note.setObjectName('subtitle')
        self.di_note.setWordWrap(True)
        di.addWidget(self.di_note)
        tables = QHBoxLayout()
        tables.setSpacing(12)
        self.pair_table = _table(('Пара атомов', 'DI'))
        self.atom_table = _table(('Атом', 'Локализация LI', 'Валентность'))
        tables.addWidget(self.pair_table, 3)
        tables.addWidget(self.atom_table, 2)
        di.addLayout(tables, 1)
        row = QHBoxLayout()
        self.di_button = QPushButton(tr('Посчитать индексы делокализации'))
        self.di_button.setObjectName('primary')
        self.di_button.clicked.connect(self.compute_di)
        row.addWidget(self.di_button)
        row.addStretch(1)
        di.addLayout(row)
        column.addWidget(di_card, 3)
        self.status = QLabel()
        self.status.setObjectName('subtitle')
        self.status.setWordWrap(True)
        column.addWidget(self.status)

    orbitals = None  # () -> the file of orbitals of the result (its .gbw or Molden), not converted

    def set_source(self, geometry, multiwfn, orbitals=None):
        self.geometry, self.multiwfn = geometry, multiwfn
        if orbitals is not None:
            self.orbitals = orbitals

    def load_saved(self):
        """When the tab is opened, once per result — the indices and the
        aromaticity Multiwfn computed before for these orbitals (field_tables.saved_output), not computed again.
        True when something was shown."""
        if getattr(self, '_saved_tried', False) or self.molecule is None or self.orbitals is None:
            return False
        self._saved_tried = True
        from modules.spectrum.wavefunction import field_tables

        try:
            orbitals = self.orbitals()
        except (AttributeError, OSError):
            orbitals = None
        if orbitals is None:
            return False
        shown = False
        text = field_tables.saved_output(orbitals, 'delocalization')
        if text:
            try:
                lidi = delocalization.parse_lidi(text)
            except (ValueError, IndexError):
                lidi = None
            if lidi is not None and lidi['di'].shape[0] == len(self.molecule.atoms):
                self.show_lidi(lidi)
                shown = True
        text = field_tables.saved_output(orbitals, 'aromaticity')
        if text and self.rings:
            try:
                values = delocalization.parse_rings(text)
            except (ValueError, IndexError):
                values = None
            if values and any(values.values()):
                self.ring_values = values
                self.fill_rings()
                shown = True
        if shown:
            self.status.setText(tr('Посчитано раньше по этому же файлу орбиталей (вывод Multiwfn — в «Анализ»); кнопки '
                                   'считают заново.'))
        return shown

    def name(self, k):
        return f'{self.molecule.atoms[k].symbol}{k + 1}'

    def show_result(self):
        """A new result: its rings with HOMA; the indices of Multiwfn are asked for by the buttons."""
        from modules.compass.chemistry.builder import connections

        self.lidi = self.ring_values = None
        self._saved_tried = False  # what was computed before — when the tab is opened (load_saved)
        self.molecule = self.geometry() if self.geometry is not None else None
        self.rings = delocalization.rings(self.molecule, connections(self.molecule)) if self.molecule is not None else []
        self.fill_rings()
        _fill(self.pair_table, [])
        _fill(self.atom_table, [])
        # whether Multiwfn is there is asked when a button is pressed: an ORCA .gbw is turned into Molden only then
        self.di_button.setEnabled(self.multiwfn is not None and self.molecule is not None)
        self.rings_button.setEnabled(self.multiwfn is not None and bool(self.rings))
        self.status.setText('')
        return self.rings

    def _source(self):
        source = self.multiwfn() if self.multiwfn is not None else None
        if not source:
            self.status.setText(tr('Индексы делокализации считает Multiwfn по файлу орбиталей результата — он не найден '
                                   'или файла орбиталей нет.'))
        return source

    def fill_rings(self):
        rows = []
        values = self.ring_values or {}
        six = [k for k, r in enumerate(self.rings) if len(r) == 6]
        for k, ring in enumerate(self.rings):
            h = delocalization.homa(self.molecule, ring)
            flu = values.get('flu', [])
            mci = values.get('mci', [])
            pdi = values.get('pdi', [])
            rows.append((
                '–'.join(self.name(a) for a in ring),
                '' if h is None else f'{h:.3f}',
                f'{flu[k]:.4f}' if k < len(flu) else '',
                f'{pdi[six.index(k)]:.4f}' if k in six and six.index(k) < len(pdi) else ('—' if values else ''),
                f'{mci[k][0]:.4f}' if k < len(mci) else '',
                f'{mci[k][1]:.4f}' if k < len(mci) else '',
            ))
        if not rows:
            rows = [(tr('Циклов из 5–7 атомов нет'), '', '', '', '', '')]
        _fill(self.ring_table, rows)

    def _work(self, title, work):
        from azimuth.tasks import run_waiting

        try:
            return run_waiting(self, title, work)
        except InterruptedError:
            return None
        except (OSError, ValueError) as exc:
            self.status.setText(str(exc))
            return None

    def compute_di(self):
        source = self._source()
        if not source or self.molecule is None:
            return False
        program, path, cores = source
        found = self._work(tr('Индексы делокализации…'),
                           lambda step: delocalization.run_lidi(program, path, cores, step))
        if found is None:
            return False
        lidi, text = found
        if lidi['di'].shape[0] != len(self.molecule.atoms):
            self.status.setText(tr('Другое число атомов, чем у результата — индексы не взяты.'))
            return False
        from modules.spectrum.wavefunction import field_tables

        field_tables.save_output(path, 'delocalization', text)
        self.show_lidi(lidi)
        return True

    def show_lidi(self, lidi):
        self.lidi = lidi
        di = lidi['di']
        n = di.shape[0]
        pairs = sorted(((di[i, j], i, j) for i in range(n) for j in range(i + 1, n) if di[i, j] >= FLOOR), reverse=True)
        _fill(self.pair_table, [(f'{self.name(i)}–{self.name(j)}', f'{v:.3f}') for v, i, j in pairs])
        li = lidi['li'] if lidi['li'] is not None else [float('nan')] * n
        _fill(self.atom_table, [(self.name(k), f'{li[k]:.3f}', f'{di[k, k]:.3f}') for k in range(n)])
        self.status.setText(tr(f'Пар с DI ≥ {FLOOR:g}: {len(pairs)}. Вывод Multiwfn — в папке «Анализ».'))
        return len(pairs)

    def compute_rings(self):
        source = self._source()
        if not source or not self.rings:
            return False
        program, path, cores = source
        found = self._work(tr('Ароматичность циклов…'),
                           lambda step: delocalization.run_rings(program, path, self.rings, cores, step))
        if found is None:
            return False
        values, text = found
        from modules.spectrum.wavefunction import field_tables

        field_tables.save_output(path, 'aromaticity', text)
        self.ring_values = values
        self.fill_rings()
        self.status.setText(tr('FLU, PDI и MCI посчитаны (нечёткие атомы Беке). Вывод Multiwfn — в папке «Анализ».'))
        return True
